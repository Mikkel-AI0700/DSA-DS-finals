class Room:
    def __init__ (
        self,
        s_name_booker: str,
        s_ref_num_booker: int,
        time_slot_start: int,
        time_slot_end: int,
        date: str
    ):
        self.room_s_name = s_name_booker
        self.room_s_ref_num = s_ref_num_booker
        self.room_ts_start = time_slot_start
        self.room_ts_end = time_slot_end
        self.room_date = date
        
class LoginRequestDetails:
    def __init__ (self, entity_ref_number: int, entity_password: str):
        self.entity_number = entity_ref_number
        self.entity_password = entity_password

class StudentBookingRequest:
    def __init__ (
        self,
        student_name: str,
        student_reference_number: int,
        requested_time_slot_start: str,
        requested_time_slot_end: str,
        requested_date: str
    ):
        self.s_name = student_name
        self.s_ref_num = student_reference_number
        self.time_slot_start = requested_time_slot_start
        self.time_slot_end = requested_time_slot_end
        self.date_requested = requested_date