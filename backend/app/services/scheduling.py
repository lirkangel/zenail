from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


SLOT_MINUTES = 15


def day_bounds_utc(d: date) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def combine_date_time_utc(d: date, t: time) -> datetime:
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second, tzinfo=timezone.utc)


def iter_slots(
    *,
    day: date,
    open_time: time,
    close_time: time,
    duration_minutes: int,
    step_minutes: int = SLOT_MINUTES,
) -> list[datetime]:
    open_dt = combine_date_time_utc(day, open_time)
    close_dt = combine_date_time_utc(day, close_time)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    slots: list[datetime] = []
    cur = open_dt
    while cur + duration <= close_dt:
        slots.append(cur)
        cur += step
    return slots


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and a_end > b_start

