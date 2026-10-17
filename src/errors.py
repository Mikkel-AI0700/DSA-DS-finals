from models import StudentBookingRequest

class TimeslotBookedException (RuntimeError):
    def __str__ (self, request: StudentBookingRequest):
        booked_exception_msg = """
        [-] Error: The selected time frame is already full
        Date: {} | Start time: {} | End time: {}
        """
        return booked_exception_msg.format(
            request.date_requested,
            request.time_slot_start,
            request.time_slot_end
        )

class DayFullyBookedException (RuntimeError):
    def __str__ (self, request: StudentBookingRequest):
        formatted_message = """
        [-] Error: The selected day is already fully booked
        Date: {}
        """
        
        return formatted_message.format(
            request.date_requested
        )
    
class IncorrectLoginDetailsException (ValueError):
    def __str__ (self, request: StudentBookingRequest):
        formatted_message = """
        [-] Error: The login information is incorrect
        Login name: {} | Login Reference number: {}
        """
        
        return formatted_message.format(
            request.time_slot_start,
            request.time_slot_end
        )
