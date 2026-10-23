from datetime import date
from dataclasses import dataclass, field

@dataclass(frozen=True, slots=True)
class RoomTimeGridConfiguration:
    OPEN_MINUTES: int = 420                             # Opening hours in minutes format
    CLOSE_MINUTES: int = 1020                           # Closing hours in minutes format
    SLOT_LENGTH_MINUTES: int = 30                       # Length of one slot, in minutes
    SLOTS_PER_DAY: int = field(init=False)              # How many slots fit between opening and closing
    
    def __post_init__ (self):
        computed_time_slot = (
            self.CLOSE_MINUTES - self.OPEN_MINUTES
        ) // self.SLOT_LENGTH_MINUTES
        alignment_remainder = (
            self.CLOSE_MINUTES - self.OPEN_MINUTES
        ) % self.SLOT_LENGTH_MINUTES
        
        if alignment_remainder == 0:
            object.__setattr__(
                self, "SLOTS_PER_DAY", computed_time_slot
            )
        else:
            raise ValueError()

@dataclass(frozen=True)
class RoomBookingPolicyConfiguration:
    MIN_SLOTS: int = 2                                  # Shortest booking, counted in slots
    MAX_SLOTS: int = 4                                  # Longest booking, counted in slots
    MIN_GROUP_SIZE: int = 3                             # Fewest people allowed on a request
    MAX_ADVANCE_DAYS: int = 14                          # How many days ahead a booking may be made
    CLOSED_WEEKDAYS: frozenset[int] = frozenset()       # Weekdays with no bookings (0 = Monday)
    CLOSED_DATES: frozenset[date] = frozenset()         # Specific dates with no bookings
    STUDENT_ID_PATTERN: str = r"[0-9]"                  # Regex the requester ID must match (non-empty for now)

@dataclass(frozen=True)
class ReasonsConfiguration:
    CANCEL_REASONS: tuple[str, ...] = (                 # Selection of reasons an admin can choose
        "[-] Error: Room {} under maintenance",
        "[-] Error: Admin override",
        "[-] Error: Room {} has schedule conflict",
    )
    AUTO_REJECT_REASON: str = "[-] Error: Slot taken"
