from models import StudentBookingRequest

class TimeslotBookedException (Exception):
    def __init__ (self, request: StudentBookingRequest):
        super().__init__()
        self.req_date = request.date_requested
        self.req_start_time = request.time_slot_start
        self.req_end_time = request.time_slot_end
    
    def __str__ (self):
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
