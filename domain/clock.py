from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from domain.models import SimulationClock

IST = ZoneInfo("Asia/Kolkata")
DEMO_START = datetime(2026, 9, 12, 9, 0, 0, tzinfo=IST)

ClockJump = Literal["start", "plus_1_day", "plus_3_days", "supplier_delay"]

NAMED_JUMPS: dict[str, datetime] = {
    "start": DEMO_START,
    "plus_1_day": datetime(2026, 9, 13, 9, 0, 0, tzinfo=IST),
    "plus_3_days": datetime(2026, 9, 15, 9, 0, 0, tzinfo=IST),
    "supplier_delay": datetime(2026, 9, 19, 10, 0, 0, tzinfo=IST),
}

# Northstar works Monday–Saturday.
_WEEKEND = {6}  # Sunday


def default_clock() -> SimulationClock:
    return SimulationClock(now=DEMO_START)


def resolve_clock_target(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return ensure_tz(value)
    if value in NAMED_JUMPS:
        return NAMED_JUMPS[value]
    return ensure_tz(datetime.fromisoformat(value))


def ensure_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=IST)
    return value.astimezone(IST)


def is_working_day(day: date) -> bool:
    return day.weekday() not in _WEEKEND


def iter_working_days(start: date, end: date):
    current = start
    while current <= end:
        if is_working_day(current):
            yield current
        current += timedelta(days=1)


def add_working_days(start: date, count: int) -> date:
    """Return the date after `count` working days, inclusive of start if it is a working day.

    count=1 and start is a working day → start.
    count=0 → start (even if weekend).
    """
    if count <= 0:
        return start
    remaining = count
    current = start
    if not is_working_day(current):
        current += timedelta(days=1)
        while not is_working_day(current):
            current += timedelta(days=1)
    while remaining > 1:
        current += timedelta(days=1)
        if is_working_day(current):
            remaining -= 1
    return current


def next_working_day(day: date) -> date:
    current = day + timedelta(days=1)
    while not is_working_day(current):
        current += timedelta(days=1)
    return current


def working_days_between(start: date, end: date) -> int:
    """Count working days in the closed interval [start, end]."""
    if end < start:
        return 0
    return sum(1 for _ in iter_working_days(start, end))
