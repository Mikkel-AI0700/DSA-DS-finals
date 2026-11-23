import itertools
import re
from datetime import date, datetime, timedelta
from models import Status, StudentBookingRequest
from config import (
    ReasonsConfiguration,
    RoomBookingPolicyConfiguration,
    RoomTimeGridConfiguration,
)
from errors import (
    DayFullyBookedException,
    InvalidBookingDateException,
    InvalidDateFormatException,
    InvalidGroupSizeException,
    InvalidStudentIdException,
    InvalidTimeRangeException,
    PastTimeSlotException,
    TimeslotBookedException,
    UnknownRoomException,
)
from time_utils import (
    ActiveReservationTimer,
    get_earliest_bookable_slot,
    slot_to_time,
    time_to_slot,
)
from booking_scheduler import (
    book_request,
    cancel_booking,
    day_trees,
    get_available_slots,
    get_day_bookings,
    req_free_from_conflicts,
    rtg_config,
    schedule_lock,
)

policy_config = RoomBookingPolicyConfiguration()
reasons_config = ReasonsConfiguration()

# request_id -> StudentBookingRequest (PENDING, APPROVED, REJECTED, COMPLETED)
all_requests: dict[int, StudentBookingRequest] = {}

# Cancelled requests are moved here with status CANCELLED and reason filled in
cancel_log: list[StudentBookingRequest] = []

request_id_counter = itertools.count(1)

reservation_timer = ActiveReservationTimer(day_trees, schedule_lock, rtg_config)


def get_time_grid_config() -> RoomTimeGridConfiguration:
    return rtg_config


def get_policy_config() -> RoomBookingPolicyConfiguration:
    return policy_config


def get_cancel_reasons() -> tuple[str, ...]:
    return reasons_config.CANCEL_REASONS


def _parse_iso_date(date_str: str) -> date:
    try:
        parsed = date.fromisoformat(date_str)
    except ValueError as exc:
        raise InvalidDateFormatException(date_str) from exc

    if parsed.isoformat() != date_str:
        raise InvalidDateFormatException(date_str)
    return parsed


def intervals_overlap(
    req_a: StudentBookingRequest,
    req_b: StudentBookingRequest,
) -> bool:
    """Symmetric binary conflict relation over half-open slot intervals [s, e)."""
    return (
        req_a.room_number == req_b.room_number
        and req_a.date_requested == req_b.date_requested
        and req_a.time_slot_start < req_b.time_slot_end
        and req_b.time_slot_start < req_a.time_slot_end
    )


def submit_request(
    student_name: str,
    student_ref_num: int,
    room_number: str,
    date_str: str,
    start_str: str,
    end_str: str,
    custom_now: datetime | None = None,
    group_size: int = policy_config.MIN_GROUP_SIZE,
    purpose: str = "",
) -> StudentBookingRequest:
    # Predicate P1: Room membership (room_number in ROOMS)
    if room_number not in policy_config.ROOMS:
        temp_request = StudentBookingRequest(
            student_name,
            student_ref_num,
            room_number,
            0,
            0,
            date.today(),
        )
        raise UnknownRoomException(temp_request)

    # Predicate P2: Valid student reference ID pattern
    if re.search(policy_config.STUDENT_ID_PATTERN, str(student_ref_num)) is None:
        raise InvalidStudentIdException(student_ref_num, policy_config.STUDENT_ID_PATTERN)

    # Predicate P3: Minimum group size requirement
    if group_size < policy_config.MIN_GROUP_SIZE:
        raise InvalidGroupSizeException(group_size, policy_config.MIN_GROUP_SIZE)

    current_time = datetime.now() if custom_now is None else custom_now
    today = current_time.date()

    # Predicate P4: Valid date format & allowed booking window / open days
    booking_date = _parse_iso_date(date_str)
    max_date = today + timedelta(days=policy_config.MAX_ADVANCE_DAYS)

    if (
        booking_date < today
        or booking_date > max_date
        or booking_date in policy_config.CLOSED_DATES
        or booking_date.weekday() in policy_config.CLOSED_WEEKDAYS
    ):
        raise InvalidBookingDateException(date_str, today, max_date)

    # Predicate P5: Valid slot boundaries, operating hours, and duration bounds
    start_slot = time_to_slot(start_str, rtg_config)
    end_slot = time_to_slot(end_str, rtg_config)

    min_minutes = policy_config.MIN_SLOTS * rtg_config.SLOT_LENGTH_MINUTES
    max_minutes = policy_config.MAX_SLOTS * rtg_config.SLOT_LENGTH_MINUTES

    if start_slot >= end_slot:
        raise InvalidTimeRangeException(start_str, end_str, min_minutes, max_minutes)

    slot_count = end_slot - start_slot
    if slot_count < policy_config.MIN_SLOTS or slot_count > policy_config.MAX_SLOTS:
        raise InvalidTimeRangeException(start_str, end_str, min_minutes, max_minutes)

    # Predicate P6: Not booking a slot that has already started today
    if booking_date == today:
        earliest_slot = get_earliest_bookable_slot(current_time, rtg_config)
        if start_slot < earliest_slot:
            earliest_time_str = slot_to_time(earliest_slot, rtg_config)
            raise PastTimeSlotException(start_str, earliest_time_str)

    new_id = next(request_id_counter)
    request = StudentBookingRequest(
        student_name,
        student_ref_num,
        room_number,
        start_slot,
        end_slot,
        booking_date,
        request_id=new_id,
        group_size=group_size,
        purpose=purpose,
    )

    try:
        req_free_from_conflicts(request)
    except (DayFullyBookedException, TimeslotBookedException) as conflict_err:
        request.status = Status.REJECTED
        request.reason = str(conflict_err)

    all_requests[new_id] = request
    return request


def cancel_own_request(request_id: int, student_ref_num: int) -> StudentBookingRequest:
    request = all_requests.get(request_id)

    if request is None:
        raise ValueError("Request ID not found: {}".format(request_id))
    if request.s_ref_num != student_ref_num:
        raise ValueError("Students can only cancel their own requests")
    if request.status != Status.PENDING:
        raise ValueError("Only PENDING requests can be cancelled by a student")

    request.status = Status.CANCELLED
    request.reason = "Cancelled by student"
    cancel_log.append(request)
    del all_requests[request_id]

    return request


def get_student_requests(student_ref_num: int) -> list[StudentBookingRequest]:
    return [
        request
        for request in all_requests.values()
        if request.s_ref_num == student_ref_num
    ]


def get_room_requests(
    room_number: str,
    date_str: str | None = None,
) -> list[StudentBookingRequest]:
    target_date = _parse_iso_date(date_str) if date_str is not None else None
    return [
        request
        for request in all_requests.values()
        if request.room_number == room_number
        and (target_date is None or request.date_requested == target_date)
    ]


def list_pending_requests() -> list[StudentBookingRequest]:
    return [
        request
        for request in all_requests.values()
        if request.status == Status.PENDING
    ]


def build_pending_conflict_graph(
    room_number: str,
    date_str: str | None = None,
) -> dict[int, set[int]]:
    """Build an undirected Interval Conflict Graph G = (V, E) over PENDING requests.

    Vertices are request IDs; an edge (u, v) exists iff requests u and v share
    the same room and date and their half-open slot intervals overlap.
    """
    pending = [
        req
        for req in get_room_requests(room_number, date_str)
        if req.status == Status.PENDING and req.request_id is not None
    ]
    adjacency: dict[int, set[int]] = {req.request_id: set() for req in pending}

    for i, req_a in enumerate(pending):
        for req_b in pending[i + 1 :]:
            if intervals_overlap(req_a, req_b):
                adjacency[req_a.request_id].add(req_b.request_id)
                adjacency[req_b.request_id].add(req_a.request_id)

    return adjacency


def suggest_max_non_conflicting_approvals(
    room_number: str,
    date_str: str | None = None,
) -> list[StudentBookingRequest]:
    """Find a Maximum Independent Set on the pending interval conflict graph.

    For interval graphs, sorting each day's pending requests by earliest end
    slot and greedily selecting non-overlapping requests yields an optimal
    maximum-cardinality conflict-free set.
    """
    pending = [
        req
        for req in get_room_requests(room_number, date_str)
        if req.status == Status.PENDING
    ]
    by_date: dict[date, list[StudentBookingRequest]] = {}
    for req in pending:
        by_date.setdefault(req.date_requested, []).append(req)

    selected: list[StudentBookingRequest] = []
    for booking_date in sorted(by_date):
        day_pending = sorted(
            by_date[booking_date],
            key=lambda r: (r.time_slot_end, r.time_slot_start, r.request_id or 0),
        )
        last_end = -1
        for req in day_pending:
            if req.time_slot_start >= last_end:
                selected.append(req)
                last_end = req.time_slot_end

    return selected


def approve_suggested_requests(
    room_number: str,
    date_str: str | None = None,
) -> list[StudentBookingRequest]:
    """Approve every request in the optimal non-conflicting suggestion set."""
    suggested = suggest_max_non_conflicting_approvals(room_number, date_str)
    approved: list[StudentBookingRequest] = []
    for req in suggested:
        if req.request_id is not None and req.status == Status.PENDING:
            result = approve_request(req.request_id)
            if result.status == Status.APPROVED:
                approved.append(result)
    return approved


def approve_request(request_id: int) -> StudentBookingRequest:
    request = all_requests.get(request_id)

    if request is None:
        raise ValueError("Request ID not found: {}".format(request_id))
    if request.status != Status.PENDING:
        raise ValueError("Only PENDING requests can be approved")

    try:
        book_request(request)
    except (DayFullyBookedException, TimeslotBookedException) as conflict_err:
        request.status = Status.REJECTED
        request.reason = str(conflict_err)
        return request

    # Auto-reject other PENDING requests on the same room and date that overlap
    for other_request in all_requests.values():
        if other_request.request_id == request.request_id:
            continue
        if other_request.status != Status.PENDING:
            continue
        if intervals_overlap(request, other_request):
            other_request.status = Status.REJECTED
            other_request.reason = reasons_config.AUTO_REJECT_REASON

    return request


def admin_cancel_request(request_id: int, reason_index: int) -> StudentBookingRequest:
    request = all_requests.get(request_id)

    if request is None:
        raise ValueError("Request ID not found: {}".format(request_id))
    if reason_index < 0 or reason_index >= len(reasons_config.CANCEL_REASONS):
        raise ValueError("Invalid cancel reason index: {}".format(reason_index))

    if request.status == Status.APPROVED:
        cancel_booking(request)

    reason_template = reasons_config.CANCEL_REASONS[reason_index]
    request.status = Status.CANCELLED
    request.reason = reason_template.format(request.room_number)
    cancel_log.append(request)
    del all_requests[request_id]

    return request


def get_day_schedule(
    room_number: str,
    date_str: str,
) -> list[tuple[str, str, StudentBookingRequest]]:
    if room_number not in policy_config.ROOMS:
        temp_request = StudentBookingRequest("", 0, room_number, 0, 0, date.today())
        raise UnknownRoomException(temp_request)

    target_date = _parse_iso_date(date_str)
    intervals = get_day_bookings(room_number, target_date)
    schedule_entries: list[tuple[str, str, StudentBookingRequest]] = []

    for interval in intervals:
        start_time = slot_to_time(interval.begin, rtg_config)
        end_time = slot_to_time(interval.end, rtg_config)
        schedule_entries.append((start_time, end_time, interval.data))

    return schedule_entries


def get_available_time_ranges(
    room_number: str,
    date_str: str,
) -> list[tuple[str, str]]:
    """Return contiguous free time ranges derived from set difference U \\ B."""
    if room_number not in policy_config.ROOMS:
        temp_request = StudentBookingRequest("", 0, room_number, 0, 0, date.today())
        raise UnknownRoomException(temp_request)

    target_date = _parse_iso_date(date_str)
    free_slots = sorted(get_available_slots(room_number, target_date))
    if not free_slots:
        return []

    ranges: list[tuple[str, str]] = []
    run_start = free_slots[0]
    prev_slot = free_slots[0]

    for slot in free_slots[1:]:
        if slot == prev_slot + 1:
            prev_slot = slot
        else:
            ranges.append(
                (slot_to_time(run_start, rtg_config), slot_to_time(prev_slot + 1, rtg_config))
            )
            run_start = slot
            prev_slot = slot

    ranges.append(
        (slot_to_time(run_start, rtg_config), slot_to_time(prev_slot + 1, rtg_config))
    )
    return ranges


def get_week_schedule(
    room_number: str,
    start_date_str: str,
) -> dict[date, list[tuple[str, str, StudentBookingRequest]]]:
    start_date = _parse_iso_date(start_date_str)
    week_schedule: dict[date, list[tuple[str, str, StudentBookingRequest]]] = {}

    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        week_schedule[current_date] = get_day_schedule(
            room_number,
            current_date.isoformat(),
        )

    return week_schedule


def start_service() -> None:
    reservation_timer.start()


def stop_service() -> None:
    reservation_timer.stop()

