from datetime import date
from models import StudentBookingRequest
from config import RoomTimeGridConfiguration

rtg_config = RoomTimeGridConfiguration()

def format_slot_value (slot_or_str: int | str) -> str:
    if isinstance(slot_or_str, int):
        total_minutes = rtg_config.OPEN_MINUTES + slot_or_str * rtg_config.SLOT_LENGTH_MINUTES
        return "{:02d}:{:02d}".format(total_minutes // 60, total_minutes % 60)
    else:
        return str(slot_or_str)

class TimeslotBookedException (Exception):
    def __init__ (
        self,
        request: StudentBookingRequest,
        conflicting_request: StudentBookingRequest | None = None
    ):
        super().__init__()
        self.req_date = request.date_requested
        self.req_start_time = format_slot_value(request.time_slot_start)
        self.req_end_time = format_slot_value(request.time_slot_end)
        
        if conflicting_request is not None:
            self.conflict_start_time = format_slot_value(conflicting_request.time_slot_start)
            self.conflict_end_time = format_slot_value(conflicting_request.time_slot_end)
        else:
            self.conflict_start_time = None
            self.conflict_end_time = None
    
    def __str__ (self):
        if self.conflict_start_time is not None and self.conflict_end_time is not None:
            booked_exception_msg = """
            [-] Error: The selected time frame is already full
            Date: {} | Start time: {} | End time: {} | Conflicting schedule: {} - {}
            """
            return booked_exception_msg.format(
                self.req_date,
                self.req_start_time,
                self.req_end_time,
                self.conflict_start_time,
                self.conflict_end_time
            )
        else:
            booked_exception_msg = """
            [-] Error: The selected time frame is already full
            Date: {} | Start time: {} | End time: {}
            """
            return booked_exception_msg.format(
                self.req_date,
                self.req_start_time,
                self.req_end_time
            )
        
class DayFullyBookedException (Exception):
    def __init__ (self, request: StudentBookingRequest):
        super().__init__()
        self.req_date = request.date_requested
    
    def __str__ (self):
        formatted_message = """
        [-] Error: The selected day is already fully booked
        Date: {}
        """
        
        return formatted_message.format(self.req_date)
    
class IncorrectLoginDetailsException (Exception):
    def __init__ (self, request: StudentBookingRequest):
        super().__init__()
        self.req_name = request.s_name
        self.req_ref = request.s_ref_num
    
    def __str__ (self):
        formatted_message = """
        [-] Error: The login information is incorrect
        Login name: {} | Login Reference number: {}
        """
        
        return formatted_message.format(
            self.req_name,
            self.req_ref
        )
        
class UnknownRoomException (Exception):
    def __init__ (self, request: StudentBookingRequest):
        super().__init__()
        self.req_room_num = request.room_number
        
    def __str__ (self):
        formatted_message = """
        [-] Error: Requested room number is unavailable
        Room number: {}
        """
        
        return formatted_message.format(self.req_room_num)

class InvalidTimeFormatException (Exception):
    def __init__ (self, time_str: str):
        super().__init__()
        self.time_str = time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid time format entered
        Entered time: {} | Expected format: HH:MM (24-hour, e.g. 09:00)
        """
        
        return formatted_message.format(self.time_str)

class InvalidDateFormatException (Exception):
    def __init__ (self, date_str: str):
        super().__init__()
        self.date_str = date_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid date format entered
        Entered date: {} | Expected format: YYYY-MM-DD (e.g. 2026-10-28)
        """
        
        return formatted_message.format(self.date_str)

class InvalidSlotBoundaryException (Exception):
    def __init__ (self, time_str: str, slot_length_minutes: int):
        super().__init__()
        self.time_str = time_str
        self.slot_length_minutes = slot_length_minutes
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Time does not align with a valid slot boundary
        Entered time: {} | Required interval: {} minutes (e.g. :00 or :30)
        """
        
        return formatted_message.format(
            self.time_str,
            self.slot_length_minutes
        )

class OutsideOperatingHoursException (Exception):
    def __init__ (self, time_str: str, open_time_str: str, close_time_str: str):
        super().__init__()
        self.time_str = time_str
        self.open_time_str = open_time_str
        self.close_time_str = close_time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Entered time is outside library operating hours
        Entered time: {} | Operating hours: {} - {}
        """
        
        return formatted_message.format(
            self.time_str,
            self.open_time_str,
            self.close_time_str
        )

class InvalidTimeRangeException (Exception):
    def __init__ (
        self,
        start_str: str,
        end_str: str,
        min_minutes: int,
        max_minutes: int
    ):
        super().__init__()
        self.start_str = start_str
        self.end_str = end_str
        self.min_minutes = min_minutes
        self.max_minutes = max_minutes
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid booking time range duration
        Start time: {} | End time: {} | Allowed duration: {} to {} minutes
        """
        
        return formatted_message.format(
            self.start_str,
            self.end_str,
            self.min_minutes,
            self.max_minutes
        )

class PastTimeSlotException (Exception):
    def __init__ (self, start_str: str, earliest_time_str: str):
        super().__init__()
        self.start_str = start_str
        self.earliest_time_str = earliest_time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Selected start time has already passed for today
        Entered start time: {} | Earliest available time today: {}
        """
        
        return formatted_message.format(
            self.start_str,
            self.earliest_time_str
        )

class InvalidBookingDateException (Exception):
    def __init__ (self, date_str: str, min_date: date, max_date: date):
        super().__init__()
        self.date_str = date_str
        self.min_date = min_date
        self.max_date = max_date
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Selected date is unavailable for booking
        Entered date: {} | Allowed date range: {} to {}
        """
        
        return formatted_message.format(
            self.date_str,
            self.min_date,
            self.max_date
        )

class InvalidTimeFormatException (Exception):
    def __init__ (self, time_str: str):
        super().__init__()
        self.time_str = time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid time format entered
        Entered time: {} | Expected format: HH:MM (24-hour, e.g. 09:00)
        """
        
        return formatted_message.format(self.time_str)

class InvalidDateFormatException (Exception):
    def __init__ (self, date_str: str):
        super().__init__()
        self.date_str = date_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid date format entered
        Entered date: {} | Expected format: YYYY-MM-DD (e.g. 2026-10-28)
        """
        
        return formatted_message.format(self.date_str)

class InvalidSlotBoundaryException (Exception):
    def __init__ (self, time_str: str, slot_length_minutes: int):
        super().__init__()
        self.time_str = time_str
        self.slot_length_minutes = slot_length_minutes
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Time does not align with a valid slot boundary
        Entered time: {} | Required interval: {} minutes (e.g. :00 or :30)
        """
        
        return formatted_message.format(
            self.time_str,
            self.slot_length_minutes
        )

class OutsideOperatingHoursException (Exception):
    def __init__ (self, time_str: str, open_time_str: str, close_time_str: str):
        super().__init__()
        self.time_str = time_str
        self.open_time_str = open_time_str
        self.close_time_str = close_time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Entered time is outside library operating hours
        Entered time: {} | Operating hours: {} - {}
        """
        
        return formatted_message.format(
            self.time_str,
            self.open_time_str,
            self.close_time_str
        )

class InvalidTimeRangeException (Exception):
    def __init__ (
        self,
        start_str: str,
        end_str: str,
        min_minutes: int,
        max_minutes: int
    ):
        super().__init__()
        self.start_str = start_str
        self.end_str = end_str
        self.min_minutes = min_minutes
        self.max_minutes = max_minutes
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Invalid booking time range duration
        Start time: {} | End time: {} | Allowed duration: {} to {} minutes
        """
        
        return formatted_message.format(
            self.start_str,
            self.end_str,
            self.min_minutes,
            self.max_minutes
        )

class PastTimeSlotException (Exception):
    def __init__ (self, start_str: str, earliest_time_str: str):
        super().__init__()
        self.start_str = start_str
        self.earliest_time_str = earliest_time_str
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Selected start time has already passed for today
        Entered start time: {} | Earliest available time today: {}
        """
        
        return formatted_message.format(
            self.start_str,
            self.earliest_time_str
        )

class InvalidBookingDateException (Exception):
    def __init__ (self, date_str: str, min_date: date, max_date: date):
        super().__init__()
        self.date_str = date_str
        self.min_date = min_date
        self.max_date = max_date
    
    def __str__ (self):
        formatted_message = """
        [-] Error: Selected date is unavailable for booking
        Entered date: {} | Allowed date range: {} to {}
        """
        
        return formatted_message.format(
            self.date_str,
            self.min_date,
            self.max_date
        )

