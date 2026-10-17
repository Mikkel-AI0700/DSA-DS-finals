# AEA-IRC Reservation System: Project Context

## 1. Conversation so far
- You pasted Handoff v2 and I confirmed the working agreement: **DSA only, you write all code, I review and guide.**
- I flagged two issues:
  - `intake.py` exists but the prototype has no intake, so leave it unused.
  - `scheduler.py` and `service.py` were written before `config`, `errors`, and `interval_index`, so expect to revise them.
- I asked three questions, still **unanswered**:
  1. Confirm Option A for rejected and cancelled requests?
  2. Keep or drop admin manual reserve?
  3. Which module to review first?

## 2. Project overview
- DLSU-D library (AEA-IRC) group study room reservation system.
- One project covers three courses (DSA, Discrete Structures, HCI). This thread is **DSA only**: queues, conflict detection, and multi-threading (deferred).
- **Team:** you (backend), Kyle (frontend), Marino (documentation).
- **Stack:** Python 3.10+, in-memory dicts, CLI first, GUI undecided.
- **Users:**
  - Students browse rooms, view day/week schedules, submit requests (group of 3 or more), and cancel their own PENDING requests.
  - Admins list pending requests, approve, and cancel with a preset reason.
  - Faculty rooms are hidden from students.

## 3. Plan: single-threaded prototype first
- No locks, workers, or race demo until the prototype works.
- Threads are added later, so:
  - `service.py` is the only entry point.
  - `scheduler.book()` is the only place that checks overlap and inserts.
  - `RoomSchedule.lock` exists but is unused.
- **Build order:**
  1. `config`, `errors`, `models`, `time_utils`
  2. `interval_index`, `scheduler`
  3. pending store
  4. `service`, `cli/main.py`
  5. unit tests
- **Definition of done:**
  1. Submit A, B (overlaps A), and C (separate).
  2. Approve A, and B is auto-rejected ("slot taken").
  3. Pending list shows C only.
  4. Admin cancels A with a preset reason. A is logged and deleted, and its slot is free.
  5. View the week.
- **Deferred:** lock, worker threads, `intake.py`, 50-thread `Barrier` race demo (expect 1 approved and 49 rejected, run with and without the lock), `test_race.py`, waitlist, GUI.

## 4. Core design

**Time → slots**

$$k = \frac{t - t_{open}}{g}, \qquad t = 60h + m$$

- $t$ is minutes since midnight, $t_{open}$ = `OPEN_MIN` (480), $g$ = `SLOT_LENGTH_MIN` (30), $k$ is the slot index.
- Check alignment first: $(t - t_{open}) \bmod g = 0$.
- Example: 10:00 gives $t=600$, so $k=\frac{600-480}{30}=4$.

**Booking** is a half-open interval $[s, e)$, so slot $k$ is occupied iff $s \le k < e$. 10:00–12:00 gives $[4, 8)$.

**Validation**

$$0 \le s < e \le N_{slots}, \quad N_{slots}=\frac{t_{close}-t_{open}}{g}=\frac{1020-480}{30}=18$$

Duration must satisfy $m_{min} \le e - s \le m_{max}$ (in slots).

**Conflict rule**

$$\text{conflict} \iff s_{new} < e_{old} \land s_{old} < e_{new}$$

- Check the new booking starts before the old one ends, and the old one starts before the new one ends.
- Against $[4,8)$: $[6,10)$ conflicts, $[5,6)$ conflicts, $[8,10)$ doesn't (back-to-back), $[0,4)$ doesn't.

**Dates**
- A booking is `(room_id, date, (s, e))`. `(room_id, date)` picks the interval tree, and only $(s,e)$ goes through the overlap rule.
- No midnight or multi-day spans. Parse with `date.fromisoformat`.
- Range: $d_{today} \le d \le d_{today} + A$ (`MAX_ADVANCE_DAYS`, 14).
- Same-day bookings are allowed. Past slots are blocked:

$$s \ge k_{now} = \max\left(0, \left\lceil \frac{t_{now}-t_{open}}{g} \right\rceil\right)$$

  - Example: 10:10 gives $\lceil 130/30 \rceil = 5$, so the earliest start is 10:30.
  - If $k_{now} \ge N_{slots}$, the day is over.
  - Integer form: `-(-(t_now - t_open) // g)`.
- Inject the clock (`now: Callable`) for testing.

**Ordering:** `time.monotonic_ns()` with `req_id` (`itertools.count()`) as tie-breaker. Never `datetime.now()`.

## 5. Locked decisions
- Only **APPROVED** requests block slots. Several PENDING requests may overlap.
- Conflict at submit is an instant rejection with a reason, with `Request.reason = str(error)`.
- **Pending store is a `dict[req_id, Request]`, not a heap.** It keeps insertion order, gives $O(1)$ lookup and delete by ID, and listing is $O(n)$. The admin can act on any ID.
- **Auto-reject:** on approval, overlapping PENDING requests on the same `(room, date)` become `REJECTED` ("slot taken"). This runs inside `scheduler.book()`. `ConflictError` stays as a guard.
- **Student:** book, and cancel own PENDING only (`service` checks the caller).
- **Admin:** approve and cancel only (any status, preset reason from `CANCEL_REASONS`). Admin "reject" is dropped.
- **Hard delete + log:** a cancel snapshots the request (`dataclasses.replace`) into an append-only log, deletes it from the dict, and removes it from the index if APPROVED. `Status.CANCELLED` only appears in log entries.
- `REJECTED` is set only by the system.
- Libraries are allowed (the DSA rubric requires no self-implemented structures).
- Group size $\ge 3$ is a validation rule only. Waitlist is on hold.

## 6. Dependencies
- **Stdlib:** `datetime`, `time`, `itertools`, `collections`, `dataclasses`, `enum`, and later `threading` and `queue`.
- **Third-party:** `intervaltree` (required), `pytest` (required), `rich` (optional), `PySide6` (GUI, undecided).
- `intervaltree` intervals are half-open, matching $[s,e)$. Wrap it in `IntervalIndex` (`overlaps`, `add`, `remove`) so the backend is swappable.
- Neither `intervaltree` nor plain dicts are thread-safe. Later: a lock for the pending store, requests dict, and log, plus one lock per room.

## 7. Structure
```
aea-irc/
├── requirements.txt, README.md
├── src/aea_irc/
│   ├── config.py  errors.py  models.py  time_utils.py
│   ├── interval_index.py  scheduler.py  pending_store.py
│   ├── intake.py (deferred)  service.py (facade)
├── cli/main.py
├── gui/            (HCI, Kyle)
├── demo/race_demo.py (deferred)
└── tests/
```
- **Import direction (downward only):** `cli/gui` → `service` → (`pending_store`, `scheduler`) → `interval_index` → leaves (`time_utils`, `models`, `config`, `errors`).
- UIs import only `service.py`. Only `scheduler.py` touches indexes. `models.py` doesn't import `config`, while `config.py` imports `Room`.

**Models:** `Status` enum, `Room` (frozen), `Request` (no `order=True`), and `RoomSchedule` (room, lock, `days` dict). The `requests` dict is the source of truth. Room status is derived on demand. Use `.get()` in read-only lookups, because `defaultdict` creates empty trees.

## 8. Config (all values are placeholders)
| Group | Parameters |
|---|---|
| Grid | `OPEN_MIN`=480, `CLOSE_MIN`=1020, `SLOT_LENGTH_MIN`=30, `SLOTS_PER_DAY`=18 (derived) |
| Policy | `MIN_SLOTS`=2, `MAX_SLOTS`=4, `MIN_GROUP_SIZE`=3, `MAX_ADVANCE_DAYS`=14, `CLOSED_WEEKDAYS`, `CLOSED_DATES`, `STUDENT_ID_PATTERN` |
| Reasons | `CANCEL_REASONS`, `AUTO_REJECT_REASON` |
| Rooms | `ROOMS: dict[str, Room]` |
| Runtime (deferred) | `NUM_WORKERS`=4, `DEMO_THREADS`=50 |

- **Derived value:** $\text{SLOTS\_PER\_DAY}=\frac{\text{CLOSE}-\text{OPEN}}{\text{SLOT\_LENGTH}}=\frac{540}{30}=18$. Compute it in `__post_init__`, never hardcode it.
- **Checks:**
  - $(\text{CLOSE}-\text{OPEN}) \bmod \text{SLOT\_LENGTH}=0$
  - `MIN_SLOTS <= MAX_SLOTS <= SLOTS_PER_DAY`
  - `MIN_GROUP_SIZE >= 1`
  - `MAX_ADVANCE_DAYS >= 0`
- **Frozen dataclasses:** use `object.__setattr__` or `field(init=False)` for derived fields, and use `frozenset` and `tuple` defaults.
- Freeze the time grid. Changing it at runtime corrupts stored $(s,e)$ values. Use `dataclasses.replace` for edits.

## 9. Errors and time utils
- **Errors:** `SchedulerError` (base), `InvalidSlotError`, `OutOfHoursError`, `InvalidGroupSizeError`, `UnknownRoomError`, `ConflictError`, `InvalidDateError`, `PastSlotError`, `ClosedDayError`, `InvalidDurationError`.
- **Probably needed:** not the owner, invalid cancel reason, unknown request, invalid status for the action.
- **`time_utils`:** `to_slot`, `to_interval`, `to_hhmm`, with the grid passed as an argument.
  - Strings live only here and in the UI.
  - `strptime` is lenient (accepts `"9:5"`), so add a round-trip check.

## 10. Request lifecycle
1. `submit_request` validates, runs a fast check against APPROVED only, then stamps and stores as PENDING (or rejects instantly).
2. Student cancel (own PENDING): log, then delete.
3. `approve(id)` calls `book()`, which rechecks, inserts, sets APPROVED, and auto-rejects overlaps.
4. Admin cancel: remove from index if APPROVED, log, delete.

**Demo assumption:** one Python process and one `service` instance, with role switching in the UI.

## 11. Open decisions
1. Where students see rejected and cancelled requests. Option A (recommended): system rejections stay as `REJECTED` in the dict, and only cancels are logged and deleted. Option B: everything is deleted and logged.
2. Keep or drop admin manual reserve.
3. Log entry format (suggested: snapshot, action, actor, timestamp, reason) and its lock later.
4. Real closing days.
5. Real requester ID format.
6. `RoomSchedule` vs. separate `schedule` and `locks` dicts (leaning `RoomSchedule`).
7. Occupied vs. reserved status.
8. Freeze the grid, and the real `SLOT_LENGTH_MIN`.

**Yours to resolve:** real hours, granularity, limits, rooms and buildings, deadline, Python version, GUI decision.

## 12. Review checklist
- `models`: snapshot with `replace` before logging.
- `time_utils`: alignment check first, and reject `"9:5"`.
- `interval_index`: boundary tests first ($[8,10)$ vs. $[4,8)$ must not conflict).
- `scheduler`: `.get()` for reads, and `book()` does recheck, insert, APPROVED, and sweep together.
- Log: all writes behind one function.
- `config`: derive `SLOTS_PER_DAY` and validate the grid.

## 13. Next step
Answer the three open questions, then paste the next module. Suggested order: `config.py`, `errors.py`, `interval_index.py`, then re-review the existing four.
