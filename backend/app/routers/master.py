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
from app.schemas.master import MasterAppointmentOut, RescheduleRequestCreate, RescheduleRequestOut
from app.services.scheduling import day_bounds_utc

router = APIRouter(tags=["master"])


@router.get("/master/appointments", response_model=list[MasterAppointmentOut])
def my_appointments(
    date_str: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_master),
) -> list[MasterAppointmentOut]:
    if staff.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can view this schedule")

    day = date.fromisoformat(date_str) if date_str else date.today()
    day_start, day_end = day_bounds_utc(day)

    appts = db.scalars(
        select(Appointment)
        .where(
            Appointment.master_id == staff.id,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
        )
        .order_by(Appointment.start_time)
    ).all()

    return [
        MasterAppointmentOut(
            id=a.id,
            branch_id=a.branch_id,
            procedure_id=a.procedure_id,
            client_name=a.client_name,
            client_phone=a.client_phone,
            start_time=a.start_time,
            end_time=a.end_time,
            price=a.price,
            status=a.status,
        )
        for a in appts
    ]


@router.get("/master/appointments/{appointment_id}", response_model=MasterAppointmentOut)
def my_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_master),
) -> MasterAppointmentOut:
    if staff.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only masters can view this schedule")

    appt = db.get(Appointment, appointment_id)
    if not appt or appt.master_id != staff.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    return MasterAppointmentOut(
        id=appt.id,
        branch_id=appt.branch_id,
        procedure_id=appt.procedure_id,
        client_name=appt.client_name,
        client_phone=appt.client_phone,
        start_time=appt.start_time,
        end_time=appt.end_time,
        price=appt.price,
        status=appt.status,
    )


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

    if payload.proposed_start_time.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="proposed_start_time must include timezone")

    branch = db.get(Branch, appt.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    proposed_end = payload.proposed_start_time + (appt.end_time - appt.start_time)
    if payload.proposed_start_time.time() < branch.open_time or proposed_end.time() > branch.close_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")

    # Avoid proposing an already-conflicting time (excluding the current appointment).
    conflict = db.scalar(
        select(Appointment).where(
            Appointment.master_id == staff.id,
            Appointment.id != appt.id,
            Appointment.status != AppointmentStatus.canceled,
            Appointment.start_time < proposed_end,
            Appointment.end_time > payload.proposed_start_time,
        )
    )
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Proposed time conflicts with another appointment")

    req = RescheduleRequest(
        appointment_id=appt.id,
        master_id=staff.id,
        proposed_start_time=payload.proposed_start_time,
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

