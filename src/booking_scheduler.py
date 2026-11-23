import threading
from datetime import date
from intervaltree import Interval, IntervalTree
from models import Status, StudentBookingRequest
from errors import DayFullyBookedException, TimeslotBookedException
from config import RoomBookingPolicyConfiguration, RoomTimeGridConfiguration

rtg_config = RoomTimeGridConfiguration()

# (room_number, date) -> IntervalTree of that room's bookings on that day
day_trees: dict[tuple[str, date], IntervalTree] = {}

# Shared with the background timer so it never reads day_trees mid-change.
# RLock (not Lock) because book_request holds it and then calls
# req_free_from_conflicts, which takes it again on the same thread.
schedule_lock = threading.RLock()


def get_day_tree(room_number: str, date_requested: date) -> IntervalTree:
    tree_key = (room_number, date_requested)

    if tree_key not in day_trees:
        day_trees[tree_key] = IntervalTree()

    return day_trees[tree_key]


def day_is_fully_booked(day_tree: IntervalTree) -> bool:
    # Merge touching bookings ([4,8) + [8,10) -> [4,10)) on a copy, then
    # the day is full when one merged interval spans every slot
    merged_tree = day_tree.copy()
    merged_tree.merge_overlaps(strict=False)

    return len(merged_tree) == 1 and merged_tree.span() >= rtg_config.SLOTS_PER_DAY


def req_free_from_conflicts(request: StudentBookingRequest) -> None:
    with schedule_lock:
        day_tree = get_day_tree(request.room_number, request.date_requested)

        if day_is_fully_booked(day_tree):
            raise DayFullyBookedException(request)

        overlapping_intervals = sorted(
            day_tree.overlap(request.time_slot_start, request.time_slot_end)
        )
        if overlapping_intervals:
            conflicting_request = overlapping_intervals[0].data
            raise TimeslotBookedException(request, conflicting_request)


def book_request(request: StudentBookingRequest) -> None:
    with schedule_lock:
        req_free_from_conflicts(request)

        day_tree = get_day_tree(request.room_number, request.date_requested)
        day_tree.addi(request.time_slot_start, request.time_slot_end, request)
        request.status = Status.APPROVED


def cancel_booking(request: StudentBookingRequest) -> None:
    with schedule_lock:
        tree_key = (request.room_number, request.date_requested)
        day_tree = day_trees.get(tree_key)

        if day_tree is not None:
            day_tree.discardi(request.time_slot_start, request.time_slot_end, request)


def get_day_bookings(room_number: str, date_requested: date) -> list[Interval]:
    with schedule_lock:
        tree_key = (room_number, date_requested)
        day_tree = day_trees.get(tree_key)

        if day_tree is None:
            return []
        return sorted(day_tree.items())


def get_available_slots(room_number: str, date_requested: date) -> set[int]:
    """Compute available slot indices via set difference U \\ B."""
    universal_slots = set(range(rtg_config.SLOTS_PER_DAY))
    booked_slots: set[int] = set()

    with schedule_lock:
        day_tree = day_trees.get((room_number, date_requested))
        if day_tree is not None:
            for interval in day_tree.items():
                booked_slots.update(range(interval.begin, interval.end))

    return universal_slots - booked_slots
