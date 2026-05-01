from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.appointment_procedure import AppointmentProcedure
from app.models.branch import Branch
from app.models.enums import AppointmentStatus


UTC = timezone.utc
SLOT_MINUTES = 15


def validate_branch_timezone(timezone_name: str) -> str:
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid branch timezone") from exc
    return timezone_name


def get_branch_timezone(branch: Branch) -> ZoneInfo:
    return ZoneInfo(validate_branch_timezone(branch.timezone))


def now_in_branch(branch: Branch) -> datetime:
    return datetime.now(UTC).astimezone(get_branch_timezone(branch))


def normalize_to_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} must include timezone",
        )
    return value.astimezone(UTC)


def ensure_branch_day_not_past(branch: Branch, *, day: date) -> None:
    if day < now_in_branch(branch).date():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot book a past date")


def ensure_branch_start_not_past(branch: Branch, *, start_utc: datetime) -> None:
    local_start = start_utc.astimezone(get_branch_timezone(branch))
    if local_start < now_in_branch(branch):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot book a past date")


def branch_day_bounds(branch: Branch, *, day: date) -> tuple[datetime, datetime]:
    tz = get_branch_timezone(branch)
    local_start = datetime.combine(day, time.min, tzinfo=tz)
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def iter_branch_slots(
    *,
    branch: Branch,
    day: date,
    duration_minutes: int,
    step_minutes: int = SLOT_MINUTES,
) -> list[datetime]:
    tz = get_branch_timezone(branch)
    open_dt = datetime.combine(day, branch.open_time, tzinfo=tz)
    close_dt = datetime.combine(day, branch.close_time, tzinfo=tz)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    slots: list[datetime] = []
    current = open_dt
    while current + duration <= close_dt:
        slots.append(current)
        current += step
    return slots


def ensure_within_branch_hours(branch: Branch, *, start_utc: datetime, end_utc: datetime) -> None:
    tz = get_branch_timezone(branch)
    local_start = start_utc.astimezone(tz)
    local_end = end_utc.astimezone(tz)

    if local_start.date() != local_end.date():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")
    if local_start.time() < branch.open_time or local_end.time() > branch.close_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")


def ensure_no_conflict(
    db: Session,
    *,
    master_id: int,
    start_utc: datetime,
    end_utc: datetime,
    exclude_appointment_id: int | None = None,
) -> None:
    stmt = select(Appointment).where(
        Appointment.master_id == master_id,
        Appointment.status != AppointmentStatus.canceled,
        Appointment.start_time < end_utc,
        Appointment.end_time > start_utc,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    conflict = db.scalar(stmt)
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot not available")


def appointment_duration_minutes(appt: Appointment) -> int:
    snapshots = list(appt.procedures)
    if snapshots:
        return sum(p.duration_minutes_snapshot for p in snapshots)
    if appt.end_time and appt.start_time:
        return int((appt.end_time - appt.start_time).total_seconds() // 60)
    if appt.procedure:
        return appt.procedure.duration_minutes
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")


def appointment_procedure_ids(appt: Appointment) -> list[int]:
    snapshots = list(appt.procedures)
    if snapshots:
        return [p.procedure_id for p in snapshots]
    return [appt.procedure_id]


def appointment_start_end(
    *,
    branch: Branch,
    start_value: datetime,
    duration_minutes: int,
    field_name: str = "start_time",
) -> tuple[datetime, datetime]:
    start_utc = normalize_to_utc(start_value, field_name=field_name)
    ensure_branch_start_not_past(branch, start_utc=start_utc)
    end_utc = start_utc + timedelta(minutes=duration_minutes)
    ensure_within_branch_hours(branch, start_utc=start_utc, end_utc=end_utc)
    return start_utc, end_utc


def snapshots_total_duration(snapshots: list[AppointmentProcedure]) -> int:
    return sum(p.duration_minutes_snapshot for p in snapshots)
