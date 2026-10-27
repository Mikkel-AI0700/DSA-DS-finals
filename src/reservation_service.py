import itertools
from datetime import date, datetime, timedelta
from models import Status, StudentBookingRequest
from config import ReasonsConfiguration, RoomBookingPolicyConfiguration
from errors import (
    DayFullyBookedException,
    TimeslotBookedException,
    UnknownRoomException
)
from time_utils import (
    ActiveReservationTimer,
    get_earliest_bookable_slot,
    slot_to_time,
    time_to_slot
)
from booking_scheduler import (
    book_request,
    cancel_booking,
    day_trees,
    get_day_bookings,
    req_free_from_conflicts,
    rtg_config,
    schedule_lock
)

policy_config = RoomBookingPolicyConfiguration()
reasons_config = ReasonsConfiguration()

# request_id -> StudentBookingRequest (PENDING, APPROVED, REJECTED, COMPLETED)
all_requests: dict[int, StudentBookingRequest] = {}

# Cancelled requests are moved here with status CANCELLED and reason filled in
cancel_log: list[StudentBookingRequest] = []

request_id_counter = itertools.count(1)

reservation_timer = ActiveReservationTimer(day_trees, schedule_lock, rtg_config)

def submit_request (
    student_name: str,
    student_ref_num: int,
    room_number: int,
    date_str: str,
    start_str: str,
    end_str: str,
    custom_now: datetime | None = None
) -> StudentBookingRequest:
    if room_number not in policy_config.ROOMS:
        temp_request = StudentBookingRequest(
            student_name,
            student_ref_num,
            room_number,
            0,
            0,
            date.today()
        )
        raise UnknownRoomException(temp_request)
    
    if custom_now is None:
        current_time = datetime.now()
    else:
        current_time = custom_now
    
    today = current_time.date()
    booking_date = date.fromisoformat(date_str)
    max_date = today + timedelta(days=policy_config.MAX_ADVANCE_DAYS)
    
    if booking_date < today:
        raise ValueError("Cannot book a past date: {}".format(date_str))
    if booking_date > max_date:
        raise ValueError("Cannot book more than {} days in advance: {}".format(
            policy_config.MAX_ADVANCE_DAYS, date_str
        ))
    if booking_date in policy_config.CLOSED_DATES:
        raise ValueError("Library is closed on date: {}".format(date_str))
    if booking_date.weekday() in policy_config.CLOSED_WEEKDAYS:
        raise ValueError("Library is closed on that weekday: {}".format(date_str))
    
    start_slot = time_to_slot(start_str, rtg_config)
    end_slot = time_to_slot(end_str, rtg_config)
    
    if start_slot >= end_slot:
        raise ValueError("Start time must be before end time: {} - {}".format(
            start_str, end_str
        ))
    
    slot_count = end_slot - start_slot
    if slot_count < policy_config.MIN_SLOTS or slot_count > policy_config.MAX_SLOTS:
        raise ValueError("Booking duration must be between {} and {} slots".format(
            policy_config.MIN_SLOTS, policy_config.MAX_SLOTS
        ))
    
    if booking_date == today:
        earliest_slot = get_earliest_bookable_slot(current_time, rtg_config)
        if start_slot < earliest_slot:
            raise ValueError("Cannot book a slot that has already started or passed: {}".format(
                start_str
            ))
    
    new_id = next(request_id_counter)
    request = StudentBookingRequest(
        student_name,
        student_ref_num,
        room_number,
        start_slot,
        end_slot,
        booking_date,
        request_id=new_id
    )
    
    try:
        req_free_from_conflicts(request)
    except (DayFullyBookedException, TimeslotBookedException) as conflict_err:
        request.status = Status.REJECTED
        request.reason = str(conflict_err)
    
    all_requests[new_id] = request
    return request

def cancel_own_request (request_id: int, student_ref_num: int) -> StudentBookingRequest:
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

def get_student_requests (student_ref_num: int) -> list[StudentBookingRequest]:
    student_list: list[StudentBookingRequest] = []
    
    for request in all_requests.values():
        if request.s_ref_num == student_ref_num:
            student_list.append(request)
    
    return student_list

def list_pending_requests () -> list[StudentBookingRequest]:
    pending_list: list[StudentBookingRequest] = []
    
    for request in all_requests.values():
        if request.status == Status.PENDING:
            pending_list.append(request)
    
    return pending_list

def approve_request (request_id: int) -> StudentBookingRequest:
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
        if other_request.room_number != request.room_number:
            continue
        if other_request.date_requested != request.date_requested:
            continue
        
        if (
            request.time_slot_start < other_request.time_slot_end
            and other_request.time_slot_start < request.time_slot_end
        ):
            other_request.status = Status.REJECTED
            other_request.reason = reasons_config.AUTO_REJECT_REASON
    
    return request

def admin_cancel_request (request_id: int, reason_index: int) -> StudentBookingRequest:
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

def get_day_schedule (
    room_number: int,
    date_str: str
) -> list[tuple[str, str, StudentBookingRequest]]:
    if room_number not in policy_config.ROOMS:
        temp_request = StudentBookingRequest("", 0, room_number, 0, 0, date.today())
        raise UnknownRoomException(temp_request)
    
    target_date = date.fromisoformat(date_str)
    intervals = get_day_bookings(room_number, target_date)
    schedule_entries: list[tuple[str, str, StudentBookingRequest]] = []
    
    for interval in intervals:
        start_time = slot_to_time(interval.begin, rtg_config)
        end_time = slot_to_time(interval.end, rtg_config)
        schedule_entries.append((start_time, end_time, interval.data))
    
    return schedule_entries

def get_week_schedule (
    room_number: int,
    start_date_str: str
) -> dict[date, list[tuple[str, str, StudentBookingRequest]]]:
    start_date = date.fromisoformat(start_date_str)
    week_schedule: dict[date, list[tuple[str, str, StudentBookingRequest]]] = {}
    
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        week_schedule[current_date] = get_day_schedule(
            room_number,
            current_date.isoformat()
        )
    
    return week_schedule

def start_service ():
    reservation_timer.start()

def stop_service ():
    reservation_timer.stop()

