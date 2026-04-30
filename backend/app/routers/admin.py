from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.enums import AppointmentStatus, RescheduleRequestStatus, StaffRole
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.reschedule_request import RescheduleRequest
from app.models.staff import Staff
from app.schemas.admin import (
    AdminAppointmentOut,
    AdminRescheduleRequestOut,
    AppointmentUpdate,
    BranchAdminOut,
    BranchCreate,
    BranchUpdate,
    MasterProcedureLink,
    ProcedureAdminOut,
    ProcedureCreate,
    ProcedureUpdate,
    RescheduleRequestDecision,
    RevenueBreakdownOut,
    RevenueBreakdownRow,
    StaffAdminOut,
    StaffCreate,
    StaffUpdate,
)
from app.services.scheduling import day_bounds_utc

router = APIRouter(tags=["admin"])


@router.get("/admin/appointments", response_model=list[AdminAppointmentOut])
def appointments(
    branch_id: int | None = Query(None),
    date_str: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> list[AdminAppointmentOut]:
    day = date.fromisoformat(date_str) if date_str else date.today()
    day_start, day_end = day_bounds_utc(day)

    stmt = (
        select(Appointment)
        .where(Appointment.start_time < day_end, Appointment.end_time > day_start)
        .order_by(Appointment.start_time)
    )
    if branch_id is not None:
        stmt = stmt.where(Appointment.branch_id == branch_id)
    appts = db.scalars(stmt).all()
    return [
        AdminAppointmentOut(
            id=a.id,
            branch_id=a.branch_id,
            master_id=a.master_id,
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


@router.patch("/admin/appointments/{appointment_id}", response_model=AdminAppointmentOut)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> AdminAppointmentOut:
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if payload.status is not None:
        appt.status = payload.status

    if payload.start_time is not None:
        if payload.start_time.tzinfo is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time must include timezone")
        proc = db.get(Procedure, appt.procedure_id)
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")
        new_start = payload.start_time
        new_end = new_start + timedelta(minutes=proc.duration_minutes)

        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        if new_start.time() < branch.open_time or new_end.time() > branch.close_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")

        conflict = db.scalar(
            select(Appointment).where(
                Appointment.master_id == appt.master_id,
                Appointment.id != appt.id,
                Appointment.status != AppointmentStatus.canceled,
                Appointment.start_time < new_end,
                Appointment.end_time > new_start,
            )
        )
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot not available")

        appt.start_time = new_start
        appt.end_time = new_end

    db.commit()
    db.refresh(appt)
    return AdminAppointmentOut(
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


@router.get("/admin/masters", response_model=list[StaffAdminOut])
def masters(
    branch_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> list[StaffAdminOut]:
    stmt = select(Staff).where(Staff.role == StaffRole.master).order_by(Staff.full_name)
    if branch_id is not None:
        stmt = stmt.where(Staff.branch_id == branch_id)
    masters = db.scalars(stmt).all()
    return [
        StaffAdminOut(
            id=m.id,
            full_name=m.full_name,
            email=m.email,
            phone=m.phone,
            role=m.role,
            branch_id=m.branch_id,
            is_active=m.is_active,
        )
        for m in masters
    ]


@router.patch("/admin/masters/{master_id}", response_model=StaffAdminOut)
def reassign_master(
    master_id: int,
    branch_id: int | None = Query(...),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> StaffAdminOut:
    master = db.get(Staff, master_id)
    if not master or master.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    master.branch_id = branch_id
    db.commit()
    db.refresh(master)
    return StaffAdminOut(
        id=master.id,
        full_name=master.full_name,
        email=master.email,
        phone=master.phone,
        role=master.role,
        branch_id=master.branch_id,
        is_active=master.is_active,
    )


@router.get("/admin/reschedule-requests", response_model=list[AdminRescheduleRequestOut])
def reschedule_requests(
    branch_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> list[AdminRescheduleRequestOut]:
    stmt = select(RescheduleRequest).order_by(RescheduleRequest.created_at.desc())
    if branch_id is not None:
        stmt = stmt.join(Appointment, Appointment.id == RescheduleRequest.appointment_id).where(
            Appointment.branch_id == branch_id
        )
    reqs = db.scalars(stmt).all()
    return [
        AdminRescheduleRequestOut(
            id=r.id,
            appointment_id=r.appointment_id,
            master_id=r.master_id,
            proposed_start_time=r.proposed_start_time,
            reason=r.reason,
            status=r.status,
            created_at=r.created_at,
            decided_by_manager_id=r.decided_by_manager_id,
            decided_at=r.decided_at,
        )
        for r in reqs
    ]


@router.patch("/admin/reschedule-requests/{request_id}", response_model=AdminRescheduleRequestOut)
def decide_reschedule_request(
    request_id: int,
    payload: RescheduleRequestDecision,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_admin),
) -> AdminRescheduleRequestOut:
    req = db.get(RescheduleRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    appt = db.get(Appointment, req.appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if req.status != RescheduleRequestStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already decided")

    if payload.status not in (RescheduleRequestStatus.approved, RescheduleRequestStatus.rejected):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")

    if payload.status == RescheduleRequestStatus.approved:
        proc = db.get(Procedure, appt.procedure_id)
        if not proc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")
        new_start = req.proposed_start_time
        new_end = new_start + timedelta(minutes=proc.duration_minutes)
        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        if new_start.time() < branch.open_time or new_end.time() > branch.close_time:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Outside branch hours")

        conflict = db.scalar(
            select(Appointment).where(
                Appointment.master_id == appt.master_id,
                Appointment.id != appt.id,
                Appointment.status != AppointmentStatus.canceled,
                Appointment.start_time < new_end,
                Appointment.end_time > new_start,
            )
        )
        if conflict:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time slot not available")
        appt.start_time = new_start
        appt.end_time = new_end

    req.status = payload.status
    req.decided_by_manager_id = staff.id
    req.decided_at = datetime.utcnow()

    db.commit()
    db.refresh(req)
    return AdminRescheduleRequestOut(
        id=req.id,
        appointment_id=req.appointment_id,
        master_id=req.master_id,
        proposed_start_time=req.proposed_start_time,
        reason=req.reason,
        status=req.status,
        created_at=req.created_at,
        decided_by_manager_id=req.decided_by_manager_id,
        decided_at=req.decided_at,
    )


@router.get("/admin/revenue", response_model=RevenueBreakdownOut)
def revenue(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> RevenueBreakdownOut:
    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid date")
    if end < start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid range")

    start_dt, _ = day_bounds_utc(start)
    _, end_dt = day_bounds_utc(end + timedelta(days=1))

    rows = db.execute(
        select(Appointment.branch_id, func.coalesce(func.sum(Appointment.price), 0))
        .where(
            Appointment.status == AppointmentStatus.completed,
            Appointment.start_time >= start_dt,
            Appointment.start_time < end_dt,
        )
        .group_by(Appointment.branch_id)
        .order_by(Appointment.branch_id)
    ).all()
    by_branch = [RevenueBreakdownRow(branch_id=r[0], total=Decimal(r[1])) for r in rows]
    total = sum((r.total for r in by_branch), Decimal("0"))
    return RevenueBreakdownOut(from_date=from_date, to_date=to_date, total=total, by_branch=by_branch)


@router.get("/admin/branches", response_model=list[BranchAdminOut])
def list_branches(db: Session = Depends(get_db), _: Staff = Depends(require_admin)) -> list[BranchAdminOut]:
    branches = db.scalars(select(Branch).order_by(Branch.name)).all()
    return [
        BranchAdminOut(
            id=b.id,
            name=b.name,
            address=b.address,
            phone=b.phone,
            open_time=b.open_time,
            close_time=b.close_time,
        )
        for b in branches
    ]


@router.post("/admin/branches", response_model=BranchAdminOut, status_code=status.HTTP_201_CREATED)
def create_branch(payload: BranchCreate, db: Session = Depends(get_db), _: Staff = Depends(require_admin)) -> BranchAdminOut:
    b = Branch(
        name=payload.name,
        address=payload.address,
        phone=payload.phone,
        open_time=payload.open_time,
        close_time=payload.close_time,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return BranchAdminOut(
        id=b.id,
        name=b.name,
        address=b.address,
        phone=b.phone,
        open_time=b.open_time,
        close_time=b.close_time,
    )


@router.patch("/admin/branches/{branch_id}", response_model=BranchAdminOut)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> BranchAdminOut:
    b = db.get(Branch, branch_id)
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return BranchAdminOut(
        id=b.id,
        name=b.name,
        address=b.address,
        phone=b.phone,
        open_time=b.open_time,
        close_time=b.close_time,
    )


@router.get("/admin/staff", response_model=list[StaffAdminOut])
def list_staff(
    role: StaffRole | None = Query(None),
    branch_id: int | None = Query(None),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> list[StaffAdminOut]:
    stmt = select(Staff).order_by(Staff.full_name)
    if role is not None:
        stmt = stmt.where(Staff.role == role)
    if branch_id is not None:
        stmt = stmt.where(Staff.branch_id == branch_id)
    rows = db.scalars(stmt).all()
    return [
        StaffAdminOut(
            id=s.id,
            full_name=s.full_name,
            email=s.email,
            phone=s.phone,
            role=s.role,
            branch_id=s.branch_id,
            is_active=s.is_active,
        )
        for s in rows
    ]


@router.post("/admin/staff", response_model=StaffAdminOut, status_code=status.HTTP_201_CREATED)
def create_staff(payload: StaffCreate, db: Session = Depends(get_db), _: Staff = Depends(require_admin)) -> StaffAdminOut:
    s = Staff(
        full_name=payload.full_name,
        email=payload.email.lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role,
        branch_id=payload.branch_id,
        is_active=payload.is_active,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return StaffAdminOut(
        id=s.id,
        full_name=s.full_name,
        email=s.email,
        phone=s.phone,
        role=s.role,
        branch_id=s.branch_id,
        is_active=s.is_active,
    )


@router.patch("/admin/staff/{staff_id}", response_model=StaffAdminOut)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> StaffAdminOut:
    s = db.get(Staff, staff_id)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
    if "password" in data:
        if data["password"]:
            s.password_hash = hash_password(data["password"])
        data.pop("password")
    for k, v in data.items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return StaffAdminOut(
        id=s.id,
        full_name=s.full_name,
        email=s.email,
        phone=s.phone,
        role=s.role,
        branch_id=s.branch_id,
        is_active=s.is_active,
    )


@router.get("/admin/procedures", response_model=list[ProcedureAdminOut])
def list_procedures(db: Session = Depends(get_db), _: Staff = Depends(require_admin)) -> list[ProcedureAdminOut]:
    procs = db.scalars(select(Procedure).order_by(Procedure.name)).all()
    return [
        ProcedureAdminOut(
            id=p.id,
            name=p.name,
            duration_minutes=p.duration_minutes,
            price=p.price,
            is_active=p.is_active,
        )
        for p in procs
    ]


@router.post("/admin/procedures", response_model=ProcedureAdminOut, status_code=status.HTTP_201_CREATED)
def create_procedure(
    payload: ProcedureCreate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> ProcedureAdminOut:
    p = Procedure(
        name=payload.name,
        duration_minutes=payload.duration_minutes,
        price=payload.price,
        is_active=payload.is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return ProcedureAdminOut(
        id=p.id,
        name=p.name,
        duration_minutes=p.duration_minutes,
        price=p.price,
        is_active=p.is_active,
    )


@router.patch("/admin/procedures/{procedure_id}", response_model=ProcedureAdminOut)
def update_procedure(
    procedure_id: int,
    payload: ProcedureUpdate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> ProcedureAdminOut:
    p = db.get(Procedure, procedure_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return ProcedureAdminOut(
        id=p.id,
        name=p.name,
        duration_minutes=p.duration_minutes,
        price=p.price,
        is_active=p.is_active,
    )


@router.post("/admin/master-procedures", status_code=status.HTTP_201_CREATED)
def link_master_procedure(
    payload: MasterProcedureLink,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> dict:
    master = db.get(Staff, payload.master_id)
    if not master or master.role != StaffRole.master:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    proc = db.get(Procedure, payload.procedure_id)
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Procedure not found")
    existing = db.scalar(
        select(MasterProcedure).where(
            MasterProcedure.master_id == payload.master_id,
            MasterProcedure.procedure_id == payload.procedure_id,
        )
    )
    if existing:
        return {"ok": True}
    db.add(MasterProcedure(master_id=payload.master_id, procedure_id=payload.procedure_id))
    db.commit()
    return {"ok": True}


@router.delete("/admin/master-procedures", status_code=status.HTTP_204_NO_CONTENT)
def unlink_master_procedure(
    master_id: int = Query(...),
    procedure_id: int = Query(...),
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> None:
    link = db.scalar(
        select(MasterProcedure).where(
            MasterProcedure.master_id == master_id,
            MasterProcedure.procedure_id == procedure_id,
        )
    )
    if link:
        db.delete(link)
        db.commit()

