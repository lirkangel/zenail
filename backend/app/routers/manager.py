from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, func, select

from app.api.deps import require_manager
from app.db.sqlmodel import get_db
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.customer import Customer, CustomerPreferenceDefinition, CustomerTagDefinition
from app.models.enums import (
    AppointmentStatus,
    RescheduleRequestStatus,
    StaffRole,
)
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.reschedule_request import RescheduleRequest
from app.models.staff import Staff
from app.schemas.manager import (
    AppointmentUpdate,
    ManagerMasterOut,
    ManagerRescheduleRequestOut,
    MasterReassign,
    RescheduleRequestDecision,
    RevenueOut,
)
from app.schemas.customer import (
    CustomerDetailOut,
    CustomerListOut,
    CustomerPreferenceDefinitionCreate,
    CustomerPreferenceDefinitionOut,
    CustomerPreferenceDefinitionUpdate,
    CustomerTagDefinitionCreate,
    CustomerTagDefinitionOut,
    CustomerTagDefinitionUpdate,
    CustomerUpdate,
)
from app.schemas.public import StaffAppointmentOut
from app.services import appointment_service
from app.services.appointment_out import appointment_to_staff_out
from app.services.booking import (
    appointment_duration_minutes,
    appointment_procedure_ids,
    appointment_start_end,
    branch_day_bounds,
    ensure_no_conflict,
    now_in_branch,
)
from app.services.customers import (
    CustomerUpdatePermissionError,
    active_customer,
    apply_customer_update,
    create_preference_definition,
    create_tag_definition,
    customer_detail_out,
    customer_is_visible,
    customer_list_out,
    list_preference_definitions,
    list_tag_definitions,
    preference_definition_out,
    tag_definition_out,
    update_preference_definition,
    update_tag_definition,
)

router = APIRouter(tags=["manager"])


def _require_branch(staff: Staff) -> int:
    if not staff.branch_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not assigned to a branch")
    return staff.branch_id


@router.get("/manager/appointments", response_model=list[StaffAppointmentOut])
def branch_appointments(
    date_str: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> list[StaffAppointmentOut]:
    branch_id = _require_branch(staff)
    branch = db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    day = date.fromisoformat(date_str) if date_str else now_in_branch(branch).date()
    day_start, day_end = branch_day_bounds(branch, day=day)

    appts = db.scalars(
        select(Appointment)
        .where(
            Appointment.branch_id == branch_id,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
        )
        .order_by(Appointment.start_time)
    ).all()

    return [appointment_to_staff_out(a) for a in appts]


@router.patch("/manager/appointments/{appointment_id}", response_model=StaffAppointmentOut)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> StaffAppointmentOut:
    branch_id = _require_branch(staff)
    appt = db.get(Appointment, appointment_id)
    if not appt or appt.branch_id != branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    did_cancel = False
    if payload.status is not None:
        if payload.status == AppointmentStatus.canceled and appt.status != AppointmentStatus.canceled:
            appointment_service.cancel(appt, db)
            did_cancel = True
        elif payload.status != AppointmentStatus.canceled:
            appt.status = payload.status

    if did_cancel:
        db.commit()
        db.refresh(appt)
        return appointment_to_staff_out(appt)

    target_master_id = payload.master_id if payload.master_id is not None else appt.master_id
    target_start = payload.start_time if payload.start_time is not None else appt.start_time
    duration_minutes = appointment_duration_minutes(appt)

    if payload.master_id is not None:
        target_master = db.get(Staff, payload.master_id)
        if (
            not target_master
            or target_master.role != StaffRole.master
            or not target_master.is_active
            or target_master.branch_id != branch_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")

        procedure_ids = appointment_procedure_ids(appt)
        available_count = db.scalar(
            select(func.count(MasterProcedure.procedure_id)).where(
                MasterProcedure.master_id == payload.master_id,
                MasterProcedure.procedure_id.in_(procedure_ids),
            )
        )
        if available_count != len(set(procedure_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Master cannot perform all procedures")

    if payload.start_time is not None or payload.master_id is not None:
        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        target_start_utc, target_end_utc = appointment_start_end(
            branch=branch,
            start_value=target_start,
            duration_minutes=duration_minutes,
        )
        ensure_no_conflict(
            db,
            master_id=target_master_id,
            start_utc=target_start_utc,
            end_utc=target_end_utc,
            exclude_appointment_id=appt.id,
        )

        appt.master_id = target_master_id
        if payload.start_time is not None:
            appointment_service.reschedule(
                appt, new_start=target_start_utc, new_end=target_end_utc, session=db
            )
        else:
            appt.start_time = target_start_utc
            appt.end_time = target_end_utc

    db.commit()
    db.refresh(appt)

    return appointment_to_staff_out(appt)


@router.get("/manager/masters", response_model=list[ManagerMasterOut])
def masters_on_branch(
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> list[ManagerMasterOut]:
    branch_id = _require_branch(staff)
    masters = db.scalars(
        select(Staff)
        .where(Staff.role == StaffRole.master, Staff.is_active.is_(True), Staff.branch_id == branch_id)
        .order_by(Staff.full_name)
    ).all()
    return [ManagerMasterOut(id=m.id, full_name=m.full_name, branch_id=m.branch_id) for m in masters]


@router.patch("/manager/masters/{master_id}", response_model=ManagerMasterOut)
def reassign_master(
    master_id: int,
    payload: MasterReassign,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> ManagerMasterOut:
    branch_id = _require_branch(staff)
    master = db.get(Staff, master_id)
    if not master or master.role != StaffRole.master or master.branch_id != branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Master not found")
    if payload.branch_id != branch_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Managers can only manage masters on their branch")
    master.branch_id = branch_id
    db.commit()
    db.refresh(master)
    return ManagerMasterOut(id=master.id, full_name=master.full_name, branch_id=master.branch_id)


@router.get("/manager/reschedule-requests", response_model=list[ManagerRescheduleRequestOut])
def list_reschedule_requests(
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> list[ManagerRescheduleRequestOut]:
    branch_id = _require_branch(staff)
    reqs = db.scalars(
        select(RescheduleRequest)
        .join(Appointment, Appointment.id == RescheduleRequest.appointment_id)
        .where(Appointment.branch_id == branch_id)
        .order_by(RescheduleRequest.created_at.desc())
    ).all()
    return [
        ManagerRescheduleRequestOut(
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


@router.patch("/manager/reschedule-requests/{request_id}", response_model=ManagerRescheduleRequestOut)
def decide_reschedule_request(
    request_id: int,
    payload: RescheduleRequestDecision,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> ManagerRescheduleRequestOut:
    branch_id = _require_branch(staff)
    req = db.get(RescheduleRequest, request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    appt = db.get(Appointment, req.appointment_id)
    if not appt or appt.branch_id != branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if req.status != RescheduleRequestStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already decided")

    if payload.status not in (RescheduleRequestStatus.approved, RescheduleRequestStatus.rejected):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid status")

    if payload.status == RescheduleRequestStatus.approved:
        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        new_start, new_end = appointment_start_end(
            branch=branch,
            start_value=req.proposed_start_time,
            duration_minutes=appointment_duration_minutes(appt),
        )
        ensure_no_conflict(
            db,
            master_id=appt.master_id,
            start_utc=new_start,
            end_utc=new_end,
            exclude_appointment_id=appt.id,
        )

        appointment_service.reschedule(appt, new_start=new_start, new_end=new_end, session=db)

    req.status = payload.status
    req.decided_by_manager_id = staff.id
    req.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(req)

    return ManagerRescheduleRequestOut(
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


@router.get("/manager/revenue", response_model=RevenueOut)
def branch_revenue(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> RevenueOut:
    branch_id = _require_branch(staff)
    branch = db.get(Branch, branch_id)
    if not branch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
    try:
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid date")
    if end < start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid range")

    start_dt, _ = branch_day_bounds(branch, day=start)
    _, end_dt = branch_day_bounds(branch, day=end + timedelta(days=1))

    total = db.scalar(
        select(func.coalesce(func.sum(Appointment.price), 0))
        .where(
            Appointment.branch_id == branch_id,
            Appointment.status == AppointmentStatus.completed,
            Appointment.start_time >= start_dt,
            Appointment.start_time < end_dt,
        )
    )
    return RevenueOut(from_date=from_date, to_date=to_date, total=Decimal(total))


@router.get("/manager/customers", response_model=CustomerListOut)
def customers(
    q: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerListOut:
    branch_id = _require_branch(staff)
    return customer_list_out(db, branch_id=branch_id, query=q, limit=limit, offset=offset)


@router.get("/manager/customers/{customer_id}", response_model=CustomerDetailOut)
def customer_detail(
    customer_id: int,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerDetailOut:
    branch_id = _require_branch(staff)
    customer = active_customer(db, customer_id=customer_id)
    if not customer or not customer_is_visible(db, customer_id=customer_id, branch_id=branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer_detail_out(db, customer=customer, branch_id=branch_id)


@router.patch("/manager/customers/{customer_id}", response_model=CustomerDetailOut)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerDetailOut:
    branch_id = _require_branch(staff)
    customer = active_customer(db, customer_id=customer_id)
    if not customer or not customer_is_visible(db, customer_id=customer_id, branch_id=branch_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    try:
        result = apply_customer_update(
            db,
            actor_id=staff.id,
            customer=customer,
            payload=payload,
            allow_phone_edit=False,
            branch_scope=branch_id,
        )
    except CustomerUpdatePermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    db.commit()
    db.refresh(result.customer)
    return customer_detail_out(
        db,
        customer=result.customer,
        branch_id=branch_id,
        merge_happened=result.merge_happened,
        merged_from_customer_id=result.merged_from_customer_id,
    )


@router.get("/manager/customer-tag-definitions", response_model=list[CustomerTagDefinitionOut])
def manager_customer_tag_definitions(
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> list[CustomerTagDefinitionOut]:
    branch_id = _require_branch(staff)
    return [tag_definition_out(row) for row in list_tag_definitions(db, branch_id=branch_id)]


@router.post(
    "/manager/customer-tag-definitions",
    response_model=CustomerTagDefinitionOut,
    status_code=status.HTTP_201_CREATED,
)
def manager_create_customer_tag_definition(
    payload: CustomerTagDefinitionCreate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerTagDefinitionOut:
    branch_id = _require_branch(staff)
    definition = create_tag_definition(actor_id=staff.id, payload=payload, branch_scope=branch_id)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return tag_definition_out(definition)


@router.patch("/manager/customer-tag-definitions/{definition_id}", response_model=CustomerTagDefinitionOut)
def manager_update_customer_tag_definition(
    definition_id: int,
    payload: CustomerTagDefinitionUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerTagDefinitionOut:
    branch_id = _require_branch(staff)
    definition = db.get(CustomerTagDefinition, definition_id)
    if not definition or definition.branch_id != branch_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer tag definition not found")
    update_tag_definition(definition, payload=payload, branch_scope=branch_id)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return tag_definition_out(definition)


@router.get("/manager/customer-preference-definitions", response_model=list[CustomerPreferenceDefinitionOut])
def manager_customer_preference_definitions(
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> list[CustomerPreferenceDefinitionOut]:
    branch_id = _require_branch(staff)
    return [preference_definition_out(row) for row in list_preference_definitions(db, branch_id=branch_id)]


@router.post(
    "/manager/customer-preference-definitions",
    response_model=CustomerPreferenceDefinitionOut,
    status_code=status.HTTP_201_CREATED,
)
def manager_create_customer_preference_definition(
    payload: CustomerPreferenceDefinitionCreate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerPreferenceDefinitionOut:
    branch_id = _require_branch(staff)
    definition = create_preference_definition(actor_id=staff.id, payload=payload, branch_scope=branch_id)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return preference_definition_out(definition)


@router.patch(
    "/manager/customer-preference-definitions/{definition_id}",
    response_model=CustomerPreferenceDefinitionOut,
)
def manager_update_customer_preference_definition(
    definition_id: int,
    payload: CustomerPreferenceDefinitionUpdate,
    db: Session = Depends(get_db),
    staff: Staff = Depends(require_manager),
) -> CustomerPreferenceDefinitionOut:
    branch_id = _require_branch(staff)
    definition = db.get(CustomerPreferenceDefinition, definition_id)
    if not definition or definition.branch_id != branch_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer preference definition not found",
        )
    update_preference_definition(definition, payload=payload, branch_scope=branch_id)
    db.add(definition)
    db.commit()
    db.refresh(definition)
    return preference_definition_out(definition)
