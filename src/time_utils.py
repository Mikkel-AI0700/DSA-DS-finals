import threading
from datetime import date, datetime
from intervaltree import IntervalTree
from models import Status
from config import RoomTimeGridConfiguration

def time_to_minutes (time_str: str) -> int:
    parsed_time = datetime.strptime(time_str, "%H:%M")
    
    # strptime also accepts "9:5", so make sure the text round-trips exactly
    if parsed_time.strftime("%H:%M") != time_str:
        raise ValueError("Time must be in HH:MM format: {}".format(time_str))
    
    return parsed_time.hour * 60 + parsed_time.minute

def time_to_slot (time_str: str, config: RoomTimeGridConfiguration) -> int:
    total_minutes = time_to_minutes(time_str)
    
    if total_minutes < config.OPEN_MINUTES or total_minutes > config.CLOSE_MINUTES:
        raise ValueError("Time is outside library hours: {}".format(time_str))
    if (total_minutes - config.OPEN_MINUTES) % config.SLOT_LENGTH_MINUTES != 0:
        raise ValueError("Time does not line up with a slot boundary: {}".format(time_str))
    
    return (total_minutes - config.OPEN_MINUTES) // config.SLOT_LENGTH_MINUTES

def slot_to_time (slot: int, config: RoomTimeGridConfiguration) -> str:
    total_minutes = config.OPEN_MINUTES + slot * config.SLOT_LENGTH_MINUTES
    
    return "{:02d}:{:02d}".format(total_minutes // 60, total_minutes % 60)

def get_elapsed_slots (current_time: datetime, config: RoomTimeGridConfiguration) -> int:
    # How many whole slots have fully passed today (rounded down).
    # At 08:10 with a 07:00 open and 30-minute slots: 70 // 30 = 2
    current_minutes = current_time.hour * 60 + current_time.minute
    elapsed_slots = (current_minutes - config.OPEN_MINUTES) // config.SLOT_LENGTH_MINUTES
    
    if elapsed_slots < 0:
        return 0
    if elapsed_slots > config.SLOTS_PER_DAY:
        return config.SLOTS_PER_DAY
    
    return elapsed_slots

def get_earliest_bookable_slot (current_time: datetime, config: RoomTimeGridConfiguration) -> int:
    # First slot that has not started yet today (rounded up).
    # At 08:10 with a 07:00 open and 30-minute slots: ceil(70 / 30) = 3, so 08:30
    current_minutes = current_time.hour * 60 + current_time.minute
    earliest_slot = -(-(current_minutes - config.OPEN_MINUTES) // config.SLOT_LENGTH_MINUTES)
    
    if earliest_slot < 0:
        return 0
    
    return earliest_slot

class ActiveReservationTimer:
    def __init__ (
        self,
        day_trees: dict[tuple[int, date], IntervalTree],
        schedule_lock: threading.RLock,
        config: RoomTimeGridConfiguration,
        interval_seconds: int = 30
    ):
        self.day_trees = day_trees
        self.schedule_lock = schedule_lock
        self.config = config
        self.interval_seconds = interval_seconds
        self.stop_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
    
    def start (self):
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self.run_loop, daemon=True)
        self.worker_thread.start()
    
    def stop (self):
        self.stop_event.set()
        
        if self.worker_thread is not None:
            self.worker_thread.join()
            self.worker_thread = None
    
    def run_loop (self):
        while not self.stop_event.is_set():
            self.tick()
            # Sleeps like time.sleep, but wakes up right away when stop() is called
            self.stop_event.wait(self.interval_seconds)
    
    def tick (self, custom_now: datetime | None = None):
        if custom_now is None:
            current_time = datetime.now()
        else:
            current_time = custom_now
        
        today = current_time.date()
        elapsed_slots = get_elapsed_slots(current_time, self.config)
        
        with self.schedule_lock:
            for tree_key, day_tree in self.day_trees.items():
                booking_date = tree_key[1]
                
                if booking_date < today:
                    finished_bookings = day_tree.items()
                elif booking_date == today:
                    # Bookings that sit entirely inside the slots that have already passed
                    finished_bookings = day_tree.envelop(0, elapsed_slots)
                else:
                    continue
                
                for booking in finished_bookings:
                    if booking.data.status == Status.APPROVED:
                        booking.data.status = Status.COMPLETED
