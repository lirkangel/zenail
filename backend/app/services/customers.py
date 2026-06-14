from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.enums import AppointmentStatus
from app.schemas.customer import (
    CustomerAppointmentOut,
    CustomerDetailOut,
    CustomerUpdate,
    CustomerListItemOut,
    CustomerListOut,
)
from app.services.customer_merge import merge_customers

UTC = timezone.utc


@dataclass
class CustomerUpdateResult:
    customer: Customer
    merge_happened: bool = False
    merged_from_customer_id: int | None = None


class CustomerUpdatePermissionError(Exception):
    pass


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    return digits or (phone or "").strip().lower()


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    value = str(email).strip().lower()
    return value or None


def resolve_customer_for_booking(
    db: Session,
    *,
    full_name: str,
    phone: str,
    email: str | None,
) -> Customer:
    phone_normalized = normalize_phone(phone)
    customer = db.scalar(
        select(Customer).where(
            Customer.phone_normalized == phone_normalized,
            Customer.is_active.is_(True),
        )
    )
    email_normalized = normalize_email(email)
    now = datetime.now(UTC)

    if customer:
        if not customer.email and email_normalized:
            customer.email = email_normalized
        if full_name.strip() and customer.full_name.strip() == customer.phone:
            customer.full_name = full_name.strip()
        customer.updated_at = now
        db.add(customer)
        return customer

    customer = Customer(
        full_name=full_name.strip() or phone.strip(),
        phone=phone.strip(),
        phone_normalized=phone_normalized,
        email=email_normalized,
    )
    db.add(customer)
    db.flush()
    return customer


def customer_scope_stmt(*, branch_id: int | None = None, query: str | None = None):
    stmt = (
        select(Customer)
        .where(Customer.is_active.is_(True))
        .order_by(Customer.updated_at.desc(), Customer.id.desc())
    )
    if branch_id is not None:
        stmt = stmt.where(
            Customer.id.in_(
                select(Appointment.customer_id).where(
                    Appointment.branch_id == branch_id,
                    Appointment.customer_id.is_not(None),
                )
            )
        )
    if query and query.strip():
        q = f"%{query.strip().lower()}%"
        phone_q = f"%{normalize_phone(query)}%"
        stmt = stmt.where(
            or_(
                func.lower(Customer.full_name).like(q),
                func.lower(Customer.email).like(q),
                Customer.phone_normalized.like(phone_q),
            )
        )
    return stmt


def customer_is_visible(db: Session, *, customer_id: int, branch_id: int | None) -> bool:
    customer = db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        return False
    if branch_id is None:
        return True
    count = db.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.customer_id == customer_id,
            Appointment.branch_id == branch_id,
        )
    )
    return bool(count)


def customer_stats(db: Session, *, customer_id: int, branch_id: int | None = None) -> dict:
    filters = [Appointment.customer_id == customer_id]
    if branch_id is not None:
        filters.append(Appointment.branch_id == branch_id)

    visit_count = db.scalar(select(func.count(Appointment.id)).where(*filters)) or 0
    completed_spend = db.scalar(
        select(func.coalesce(func.sum(Appointment.price), 0)).where(
            *filters,
            Appointment.status == AppointmentStatus.completed,
        )
    )
    latest_visit = db.scalar(select(func.max(Appointment.start_time)).where(*filters))
    upcoming = db.scalar(
        select(func.min(Appointment.start_time)).where(
            *filters,
            Appointment.status == AppointmentStatus.scheduled,
            Appointment.start_time >= datetime.now(UTC),
        )
    )
    return {
        "visit_count": int(visit_count),
        "completed_spend": Decimal(completed_spend or 0),
        "latest_visit": latest_visit,
        "upcoming_appointment": upcoming,
    }


def customer_history(db: Session, *, customer_id: int, branch_id: int | None = None) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.customer_id == customer_id).order_by(Appointment.start_time.desc())
    if branch_id is not None:
        stmt = stmt.where(Appointment.branch_id == branch_id)
    return list(db.scalars(stmt).all())


def customer_list_out(
    db: Session,
    *,
    branch_id: int | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> CustomerListOut:
    base_stmt = customer_scope_stmt(branch_id=branch_id, query=query)
    total = db.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
    customers = db.scalars(base_stmt.limit(limit).offset(offset)).all()
    return CustomerListOut(
        items=[customer_item_out(db, customer=c, branch_id=branch_id) for c in customers],
        total=int(total),
        limit=limit,
        offset=offset,
    )


def customer_item_out(db: Session, *, customer: Customer, branch_id: int | None = None) -> CustomerListItemOut:
    stats = customer_stats(db, customer_id=customer.id, branch_id=branch_id)
    return CustomerListItemOut(
        id=customer.id,
        full_name=customer.full_name,
        phone=customer.phone,
        email=customer.email,
        notes=customer.notes,
        visit_count=stats["visit_count"],
        completed_spend=stats["completed_spend"],
        latest_visit=stats["latest_visit"],
        upcoming_appointment=stats["upcoming_appointment"],
    )


def customer_detail_out(
    db: Session,
    *,
    customer: Customer,
    branch_id: int | None = None,
    merge_happened: bool = False,
    merged_from_customer_id: int | None = None,
) -> CustomerDetailOut:
    item = customer_item_out(db, customer=customer, branch_id=branch_id)
    history = customer_history(db, customer_id=customer.id, branch_id=branch_id)
    return CustomerDetailOut(
        **item.model_dump(),
        merge_happened=merge_happened,
        merged_from_customer_id=merged_from_customer_id,
        appointments=[
            CustomerAppointmentOut(
                id=appt.id,
                branch_id=appt.branch_id,
                master_id=appt.master_id,
                master_name=appt.master.full_name if appt.master else None,
                start_time=appt.start_time,
                end_time=appt.end_time,
                price=appt.price,
                status=appt.status,
                procedures=[p.name_snapshot for p in appt.procedures]
                or ([appt.procedure.name] if appt.procedure else []),
            )
            for appt in history
        ],
    )


def active_customer(db: Session, *, customer_id: int) -> Customer | None:
    customer = db.get(Customer, customer_id)
    if not customer or not customer.is_active:
        return None
    return customer


def apply_customer_update(
    db: Session,
    *,
    actor_id: int,
    customer: Customer,
    payload: CustomerUpdate,
    allow_phone_edit: bool,
) -> CustomerUpdateResult:
    fields_set = payload.model_fields_set

    if "phone" in fields_set and not allow_phone_edit:
        raise CustomerUpdatePermissionError("Managers cannot edit phone")

    result = CustomerUpdateResult(customer=customer)

    if "full_name" in fields_set and payload.full_name is not None:
        customer.full_name = payload.full_name.strip() or customer.full_name
    if "email" in fields_set:
        customer.email = normalize_email(payload.email)
    if "notes" in fields_set:
        customer.notes = payload.notes.strip() or None if payload.notes is not None else None

    if "phone" in fields_set and payload.phone is not None:
        phone = payload.phone.strip()
        normalized_phone = normalize_phone(phone)

        with db.no_autoflush:
            collision = db.scalar(
                select(Customer).where(
                    Customer.phone_normalized == normalized_phone,
                    Customer.id != customer.id,
                    Customer.is_active.is_(True),
                )
            )
        if collision is not None:
            survivor, source = sorted([customer, collision], key=lambda row: row.id)
            survivor.phone = phone
            survivor.phone_normalized = normalized_phone
            merge_result = merge_customers(
                db,
                source=source,
                target=survivor,
                performed_by_staff_id=actor_id,
            )
            db.add(survivor)
            db.flush()
            return CustomerUpdateResult(
                customer=survivor,
                merge_happened=True,
                merged_from_customer_id=merge_result.source_customer_id,
            )

        customer.phone = phone
        customer.phone_normalized = normalized_phone

    customer.updated_at = datetime.now(UTC)
    db.add(customer)
    db.flush()
    return result
