from enum import Enum, auto
from datetime import date


class Status(Enum):
    PENDING = auto()
    APPROVED = auto()
    REJECTED = auto()
    CANCELLED = auto()
    COMPLETED = auto()


class StudentBookingRequest:
    def __init__(
        self,
        student_name: str,
        student_reference_number: int,
        requested_room_number: str,
        requested_time_slot_start: int,
        requested_time_slot_end: int,
        requested_date: date,
        request_id: int | None = None,
        group_size: int = 3,
        purpose: str = "",
    ):
        self.request_id = request_id
        self.s_name = student_name
        self.s_ref_num = student_reference_number
        self.room_number = requested_room_number
        self.time_slot_start = requested_time_slot_start
        self.time_slot_end = requested_time_slot_end
        self.date_requested = requested_date
        self.group_size = group_size
        self.purpose = purpose
        self.status = Status.PENDING
        self.reason: str | None = None
