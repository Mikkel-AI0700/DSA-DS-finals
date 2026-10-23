from enum import Enum, auto
from datetime import date
from typing import Any

try:
    from intervaltree import IntervalTree
except ImportError:
    IntervalTree = Any  # type: ignore[assignment, misc]

class Status(Enum):
    PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()
    CANCELLED = auto()

class Room:
    def __init__(self, room_number: int):
        self.room_number = room_number

class RoomSchedule:
    def __init__(
        self,
        room: Room,
        days: dict[date, IntervalTree] | None = None
    ):
        self.room = room
        self.days: dict[date, IntervalTree] = days if days is not None else {}

class LoginRequestDetails:
    def __init__(self, entity_ref_number: int, entity_password: str):
        self.entity_number = entity_ref_number
        self.entity_password = entity_password

class StudentBookingRequest:
    def __init__(
        self,
        student_name: str,
        student_reference_number: int,
        requested_room_number: int,
        requested_time_slot_start: str,
        requested_time_slot_end: str,
        requested_date: str,
        request_id: int | None = None
    ):
        self.request_id = request_id
        self.s_name = student_name
        self.s_ref_num = student_reference_number
        self.room_number = requested_room_number
        self.time_slot_start = requested_time_slot_start
        self.time_slot_end = requested_time_slot_end
        self.date_requested = requested_date
        self.status = Status.PENDING
        self.reason: str | None = None
