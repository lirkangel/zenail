from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.appointment_procedure import AppointmentProcedure
from app.models.branch import Branch
from app.models.branch_non_working_day import BranchNonWorkingDay
from app.models.enums import AppointmentStatus, StaffRole
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.staff import Staff
from app.schemas.public import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentProcedureOut,
    AvailabilityOut,
    BranchOut,
    MasterOut,
    ProcedureOut,
)
from app.services.appointment_out import appointment_to_out
from app.services.scheduling import day_bounds_utc, iter_slots

router = APIRouter(tags=["public"])


def _parse_procedure_ids(
    *,
    procedure_id: int | None = None,
    procedure_ids: str | list[int] | None = None,
) -> list[int]:
    ids: list[int] = []
    if isinstance(procedure_ids, str) and procedure_ids.strip():
        ids.extend(int(part) for part in procedure_ids.split(",") if part.strip())
    elif isinstance(procedure_ids, list):
        ids.extend(procedure_ids)
    if procedure_id is not None:
        ids.append(procedure_id)

    deduped: list[int] = []
    for value in ids:
        if value not in deduped:
            deduped.append(value)
    if not deduped:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="At least one procedure is required")
    return deduped


def _load_master_procedures(db: Session, *, master_id: int, procedure_ids: list[int]) -> list[Procedure]:
    procs = db.scalars(
        select(Procedure)
        .join(MasterProcedure, MasterProcedure.procedure_id == Procedure.id)
        .where(
            MasterProcedure.master_id == master_id,
            Procedure.id.in_(procedure_ids),
            Procedure.is_active.is_(True),
        )
    ).all()
    by_id = {p.id: p for p in procs}
    missing = [pid for pid in procedure_ids if pid not in by_id]
    if missing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not available")
    return [by_id[pid] for pid in procedure_ids]


_appointment_out = appointment_to_out


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
            description=p.description,
            category=p.category,
            duration_minutes=p.duration_minutes,
            price=p.price,
        )
        for p in procs
    ]


@router.get("/availability", response_model=AvailabilityOut)
def availability(
    master_id: int = Query(...),
    procedure_id: int | None = Query(None),
    procedure_ids: str | None = Query(None),
    date_str: str = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date")
    if day < date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot book a past date")

    master = db.scalar(select(Staff).where(Staff.id == master_id, Staff.role == StaffRole.master))
    if not master or not master.branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")

    branch = db.get(Branch, master.branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")

    selected_ids = _parse_procedure_ids(procedure_id=procedure_id, procedure_ids=procedure_ids)
    procs = _load_master_procedures(db, master_id=master_id, procedure_ids=selected_ids)
    total_duration = sum(p.duration_minutes for p in procs)
    total_price = sum((Decimal(p.price) for p in procs), Decimal("0"))

    closed = db.scalar(
        select(BranchNonWorkingDay).where(
            BranchNonWorkingDay.branch_id == branch.id,
            BranchNonWorkingDay.day == day,
        )
    )
    if closed:
        return AvailabilityOut(
            master_id=master_id,
            procedure_id=selected_ids[0],
            procedure_ids=selected_ids,
            date=date_str,
            total_duration_minutes=total_duration,
            total_price=total_price,
            slots=[],
        )

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
        duration_minutes=total_duration,
    )
    duration = timedelta(minutes=total_duration)

    free: list = []
    for start in candidates:
        end = start + duration
        if any(a.start_time < end and a.end_time > start for a in existing):
            continue
        free.append(start)

    return AvailabilityOut(
        master_id=master_id,
        procedure_id=selected_ids[0],
        procedure_ids=selected_ids,
        date=date_str,
        total_duration_minutes=total_duration,
        total_price=total_price,
        slots=free,
    )


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

    selected_ids = _parse_procedure_ids(procedure_id=payload.procedure_id, procedure_ids=payload.procedure_ids)
    procs = _load_master_procedures(db, master_id=payload.master_id, procedure_ids=selected_ids)
    total_duration = sum(p.duration_minutes for p in procs)
    total_price = sum((Decimal(p.price) for p in procs), Decimal("0"))

    start = payload.start_time
    if start.tzinfo is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must include timezone")
    if start.date() < date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot book a past date")
    end = start + timedelta(minutes=total_duration)

    closed = db.scalar(
        select(BranchNonWorkingDay).where(
            BranchNonWorkingDay.branch_id == branch.id,
            BranchNonWorkingDay.day == start.date(),
        )
    )
    if closed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Branch is closed on this day")

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
        procedure_id=selected_ids[0],
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        start_time=start,
        end_time=end,
        price=total_price,
        status=AppointmentStatus.scheduled,
    )
    db.add(appt)
    db.flush()
    for idx, proc in enumerate(procs):
        db.add(
            AppointmentProcedure(
                appointment_id=appt.id,
                procedure_id=proc.id,
                sort_order=idx,
                name_snapshot=proc.name,
                duration_minutes_snapshot=proc.duration_minutes,
                price_snapshot=Decimal(proc.price),
            )
        )
    db.commit()
    db.refresh(appt)

    return _appointment_out(appt)


@router.get("/appointments/{appointment_id}", response_model=AppointmentOut)
def get_public_appointment(
    appointment_id: int,
    client_phone: str = Query(...),
    db: Session = Depends(get_db),
) -> AppointmentOut:
    appt = db.get(Appointment, appointment_id)
    if not appt or appt.client_phone != client_phone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return _appointment_out(appt)

