from intervaltree import Interval, IntervalTree
from models import StudentBookingRequest
from errors import DayFullyBookedException, TimeslotBookedException
from config import RoomBookingPolicyConfiguration, RoomTimeGridConfiguration

rtg_config = RoomTimeGridConfiguration()

main_tree_object = IntervalTree()

def req_free_from_conflicts (interval_request: Interval, request: StudentBookingRequest):
    try:
        if len(main_tree_object) >= RoomTimeGridConfiguration.SLOTS_PER_DAY:
            raise DayFullyBookedException(request)
        if main_tree_object.overlap(interval_request.begin, interval_request.end):
            raise TimeslotBookedException(request)
    except DayFullyBookedException as dfe_except:
        print(dfe_except)
        return False
    except TimeslotBookedException as tbe_except:
        print(tbe_except)
        return False
    
def book_request (request: StudentBookingRequest):
    room_information = (
        request.s_name,
        request.s_ref_num,
    )
    
    interval_entry = Interval(
        request.time_slot_start,
        request.time_slot_end,
        room_information
    )
    
    main_tree_object.add(interval_entry)
