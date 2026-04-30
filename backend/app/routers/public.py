from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.enums import AppointmentStatus, StaffRole
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.staff import Staff
from app.schemas.public import (
    AppointmentCreate,
    AppointmentOut,
    AvailabilityOut,
    BranchOut,
    MasterOut,
    ProcedureOut,
)
from app.services.scheduling import day_bounds_utc, iter_slots

router = APIRouter(tags=["public"])


@router.get("/branches", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db)) -> list[BranchOut]:
    branches = db.scalars(select(Branch).order_by(Branch.name)).all()
    return [
        BranchOut(
            id=b.id,
            name=b.name,
            address=b.address,
            phone=b.phone,
            open_time=b.open_time,
            close_time=b.close_time,
        )
        for b in branches
    ]


@router.get("/branches/{branch_id}/masters", response_model=list[MasterOut])
def list_masters(branch_id: int, db: Session = Depends(get_db)) -> list[MasterOut]:
    masters = db.scalars(
        select(Staff)
        .where(
            Staff.branch_id == branch_id,
            Staff.role == StaffRole.master,
            Staff.is_active.is_(True),
        )
        .order_by(Staff.full_name)
    ).all()
    return [MasterOut(id=m.id, full_name=m.full_name) for m in masters]


@router.get("/masters/{master_id}/procedures", response_model=list[ProcedureOut])
def list_master_procedures(master_id: int, db: Session = Depends(get_db)) -> list[ProcedureOut]:
    procs = db.scalars(
        select(Procedure)
        .join(MasterProcedure, MasterProcedure.procedure_id == Procedure.id)
        .where(
            MasterProcedure.master_id == master_id,
            Procedure.is_active.is_(True),
        )
        .order_by(Procedure.name)
    ).all()
    return [
        ProcedureOut(
            id=p.id,
            name=p.name,
            duration_minutes=p.duration_minutes,
            price=p.price,
        )
        for p in procs
    ]


@router.get("/availability", response_model=AvailabilityOut)
def availability(
    master_id: int = Query(...),
    procedure_id: int = Query(...),
    date_str: str = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date")

    master = db.scalar(select(Staff).where(Staff.id == master_id, Staff.role == StaffRole.master))
    if not master or not master.branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")

    branch = db.get(Branch, master.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    proc = db.scalar(
        select(Procedure)
        .join(MasterProcedure, MasterProcedure.procedure_id == Procedure.id)
        .where(MasterProcedure.master_id == master_id, Procedure.id == procedure_id, Procedure.is_active.is_(True))
    )
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not available")

    day_start, day_end = day_bounds_utc(day)
    existing = db.scalars(
        select(Appointment).where(
            Appointment.master_id == master_id,
            Appointment.status != AppointmentStatus.canceled,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
        )
    ).all()

    candidates = iter_slots(
        day=day,
        open_time=branch.open_time,
        close_time=branch.close_time,
        duration_minutes=proc.duration_minutes,
    )
    duration = timedelta(minutes=proc.duration_minutes)

    free: list = []
    for start in candidates:
        end = start + duration
        if any(a.start_time < end and a.end_time > start for a in existing):
            continue
        free.append(start)

    return AvailabilityOut(master_id=master_id, procedure_id=procedure_id, date=date_str, slots=free)


@router.post("/appointments", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(payload: AppointmentCreate, db: Session = Depends(get_db)) -> AppointmentOut:
    master = db.scalar(
        select(Staff).where(
            Staff.id == payload.master_id,
            Staff.role == StaffRole.master,
            Staff.is_active.is_(True),
        )
    )
    if not master or not master.branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    if master.branch_id != payload.branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Master not in branch")

    branch = db.get(Branch, payload.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    proc = db.scalar(
        select(Procedure)
        .join(MasterProcedure, MasterProcedure.procedure_id == Procedure.id)
        .where(MasterProcedure.master_id == payload.master_id, Procedure.id == payload.procedure_id, Procedure.is_active.is_(True))
    )
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not available")

    start = payload.start_time
    if start.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must include timezone")
    end = start + timedelta(minutes=proc.duration_minutes)

    # branch hours check (UTC-based)
    if start.time() < branch.open_time or end.time() > branch.close_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")

    conflict = db.scalar(
        select(Appointment).where(
            Appointment.master_id == payload.master_id,
            Appointment.status != AppointmentStatus.canceled,
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
    )
    if conflict:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot not available")

    appt = Appointment(
        branch_id=payload.branch_id,
        master_id=payload.master_id,
        procedure_id=payload.procedure_id,
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        start_time=start,
        end_time=end,
        price=Decimal(proc.price),
        status=AppointmentStatus.scheduled,
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return AppointmentOut(
        id=appt.id,
        branch_id=appt.branch_id,
        master_id=appt.master_id,
        procedure_id=appt.procedure_id,
        client_name=appt.client_name,
        client_phone=appt.client_phone,
        start_time=appt.start_time,
        end_time=appt.end_time,
        price=appt.price,
        status=appt.status,
    )

