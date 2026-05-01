from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_master
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.enums import AppointmentStatus, RescheduleRequestStatus, StaffRole
from app.models.reschedule_request import RescheduleRequest
from app.models.staff import Staff
from app.schemas.master import RescheduleRequestCreate, RescheduleRequestOut
from app.schemas.public import AppointmentOut
from app.services.appointment_out import appointment_to_out
from app.services.booking import (
    appointment_duration_minutes,
    appointment_start_end,
    branch_day_bounds,
    ensure_no_conflict,
    now_in_branch,
)

router = APIRouter(tags=["master"])


@router.get("/master/appointments", response_model=list[AppointmentOut])
def my_appointments(
    date_str: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_master),
) -> list[AppointmentOut]:
    if staff.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can view this schedule")

    branch = db.get(Branch, staff.branch_id) if staff.branch_id else None
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    day = date.fromisoformat(date_str) if date_str else now_in_branch(branch).date()
    day_start, day_end = branch_day_bounds(branch, day=day)

    appts = db.scalars(
        select(Appointment)
        .where(
            Appointment.master_id == staff.id,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
        )
        .order_by(Appointment.start_time)
    ).all()

    return [appointment_to_out(a) for a in appts]


@router.get("/master/appointments/{appointment_id}", response_model=AppointmentOut)
def my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_master),
) -> AppointmentOut:
    if staff.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can view this schedule")

    appt = db.get(Appointment, appointment_id)
    if not appt or appt.master_id != staff.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return appointment_to_out(appt)


@router.post("/master/reschedule-requests", response_model=RescheduleRequestOut, status_code=status.HTTP_201_CREATED)
def request_reschedule(
    payload: RescheduleRequestCreate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_master),
) -> RescheduleRequestOut:
    if staff.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can request reschedule")

    appt = db.get(Appointment, payload.appointment_id)
    if not appt or appt.master_id != staff.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if appt.status == AppointmentStatus.canceled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Appointment is canceled")

    branch = db.get(Branch, appt.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    proposed_start, proposed_end = appointment_start_end(
        branch=branch,
        start_value=payload.proposed_start_time,
        duration_minutes=appointment_duration_minutes(appt),
        field_name="proposed_start_time",
    )
    ensure_no_conflict(
        db,
        master_id=staff.id,
        start_utc=proposed_start,
        end_utc=proposed_end,
        exclude_appointment_id=appt.id,
    )

    req = RescheduleRequest(
        appointment_id=appt.id,
        master_id=staff.id,
        proposed_start_time=proposed_start,
        reason=payload.reason,
        status=RescheduleRequestStatus.pending,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return RescheduleRequestOut(
        id=req.id,
        appointment_id=req.appointment_id,
        master_id=req.master_id,
        proposed_start_time=req.proposed_start_time,
        reason=req.reason,
        status=req.status,
        created_at=req.created_at,
    )
