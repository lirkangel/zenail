from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import or_
from sqlmodel import Session, func, select

from app.models.appointment import Appointment
from app.models.customer import (
    Customer,
    CustomerPreferenceDefinition,
    CustomerPreferenceValue,
    CustomerTag,
    CustomerTagDefinition,
    DefinitionScope,
)
from app.models.enums import AppointmentStatus
from app.schemas.customer import (
    CustomerAppointmentOut,
    CustomerDetailOut,
    CustomerListItemOut,
    CustomerListOut,
    CustomerPreferenceDefinitionCreate,
    CustomerPreferenceDefinitionOut,
    CustomerPreferenceDefinitionUpdate,
    CustomerPreferenceOut,
    CustomerPreferenceValueIn,
    CustomerTagDefinitionCreate,
    CustomerTagDefinitionOut,
    CustomerTagDefinitionUpdate,
    CustomerTagOut,
    CustomerUpdate,
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


def normalize_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


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


def _visible_tag_definition_stmt(*, branch_id: int | None) -> object:
    stmt = select(CustomerTagDefinition).where(CustomerTagDefinition.is_active.is_(True))
    if branch_id is not None:
        stmt = stmt.where(
            or_(
                CustomerTagDefinition.scope == DefinitionScope.global_,
                CustomerTagDefinition.branch_id == branch_id,
            )
        )
    return stmt.order_by(CustomerTagDefinition.name, CustomerTagDefinition.id)


def _visible_preference_definition_stmt(*, branch_id: int | None) -> object:
    stmt = select(CustomerPreferenceDefinition).where(CustomerPreferenceDefinition.is_active.is_(True))
    if branch_id is not None:
        stmt = stmt.where(
            or_(
                CustomerPreferenceDefinition.scope == DefinitionScope.global_,
                CustomerPreferenceDefinition.branch_id == branch_id,
            )
        )
    return stmt.order_by(CustomerPreferenceDefinition.name, CustomerPreferenceDefinition.id)


def list_tag_definitions(db: Session, *, branch_id: int | None) -> list[CustomerTagDefinition]:
    return list(db.scalars(_visible_tag_definition_stmt(branch_id=branch_id)).all())


def list_preference_definitions(db: Session, *, branch_id: int | None) -> list[CustomerPreferenceDefinition]:
    return list(db.scalars(_visible_preference_definition_stmt(branch_id=branch_id)).all())


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


def customer_tags_out(db: Session, *, customer_id: int, branch_id: int | None) -> list[CustomerTagOut]:
    defs = {definition.id: definition for definition in list_tag_definitions(db, branch_id=branch_id)}
    if not defs:
        return []
    rows = db.exec(
        select(CustomerTag).where(
            CustomerTag.customer_id == customer_id,
            CustomerTag.tag_definition_id.in_(defs.keys()),
        )
    ).all()
    return [
        CustomerTagOut(
            id=definition.id,
            name=definition.name,
            slug=definition.slug,
            scope=definition.scope,
            branch_id=definition.branch_id,
        )
        for row in rows
        if (definition := defs.get(row.tag_definition_id)) is not None
    ]


def customer_preferences_out(db: Session, *, customer_id: int, branch_id: int | None) -> list[CustomerPreferenceOut]:
    defs = {definition.id: definition for definition in list_preference_definitions(db, branch_id=branch_id)}
    if not defs:
        return []
    rows = db.exec(
        select(CustomerPreferenceValue).where(
            CustomerPreferenceValue.customer_id == customer_id,
            CustomerPreferenceValue.preference_definition_id.in_(defs.keys()),
        )
    ).all()
    return [
        CustomerPreferenceOut(
            definition_id=definition.id,
            name=definition.name,
            slug=definition.slug,
            scope=definition.scope,
            branch_id=definition.branch_id,
            value_type=definition.value_type,
            value_text=row.value_text,
            value_bool=row.value_bool,
            value_option=row.value_option,
        )
        for row in rows
        if (definition := defs.get(row.preference_definition_id)) is not None
    ]


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
        items=[customer_item_out(db, customer=customer, branch_id=branch_id) for customer in customers],
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
        tags=customer_tags_out(db, customer_id=customer.id, branch_id=branch_id),
        preferences=customer_preferences_out(db, customer_id=customer.id, branch_id=branch_id),
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


def _sync_customer_tags(
    db: Session,
    *,
    customer_id: int,
    tag_ids: list[int],
    actor_id: int,
    branch_scope: int | None,
) -> None:
    visible_ids = {definition.id for definition in list_tag_definitions(db, branch_id=branch_scope)}
    target_ids = {tag_id for tag_id in tag_ids if tag_id in visible_ids}
    if visible_ids:
        current_rows = db.exec(
            select(CustomerTag).where(
                CustomerTag.customer_id == customer_id,
                CustomerTag.tag_definition_id.in_(visible_ids),
            )
        ).all()
    else:
        current_rows = []
    current_by_id = {row.tag_definition_id: row for row in current_rows}

    for definition_id, row in current_by_id.items():
        if definition_id not in target_ids:
            db.delete(row)
    for definition_id in target_ids - current_by_id.keys():
        db.add(
            CustomerTag(
                customer_id=customer_id,
                tag_definition_id=definition_id,
                assigned_by_staff_id=actor_id,
            )
        )


def _sync_customer_preferences(
    db: Session,
    *,
    customer_id: int,
    preferences: list[CustomerPreferenceValueIn],
    actor_id: int,
    branch_scope: int | None,
) -> None:
    visible_defs = {definition.id: definition for definition in list_preference_definitions(db, branch_id=branch_scope)}
    requested_by_id = {
        preference.definition_id: preference
        for preference in preferences
        if preference.definition_id in visible_defs
    }
    if visible_defs:
        existing_rows = db.exec(
            select(CustomerPreferenceValue).where(
                CustomerPreferenceValue.customer_id == customer_id,
                CustomerPreferenceValue.preference_definition_id.in_(visible_defs.keys()),
            )
        ).all()
    else:
        existing_rows = []
    existing_by_id = {row.preference_definition_id: row for row in existing_rows}
    now = datetime.now(UTC)

    for definition_id, row in existing_by_id.items():
        if definition_id not in requested_by_id:
            db.delete(row)

    for definition_id, payload in requested_by_id.items():
        existing = existing_by_id.get(definition_id)
        if existing is None:
            db.add(
                CustomerPreferenceValue(
                    customer_id=customer_id,
                    preference_definition_id=definition_id,
                    value_text=payload.value_text,
                    value_bool=payload.value_bool,
                    value_option=payload.value_option,
                    updated_by_staff_id=actor_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            continue
        existing.value_text = payload.value_text
        existing.value_bool = payload.value_bool
        existing.value_option = payload.value_option
        existing.updated_by_staff_id = actor_id
        existing.updated_at = now
        db.add(existing)


def apply_customer_update(
    db: Session,
    *,
    actor_id: int,
    customer: Customer,
    payload: CustomerUpdate,
    allow_phone_edit: bool,
    branch_scope: int | None,
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
            # phone_normalized is UNIQUE: release the source's key before the
            # survivor takes the new phone, and so a future booking on the
            # source's old phone can create a fresh customer.
            source.phone_normalized = f"merged:{source.id}"
            db.add(source)
            db.flush()
            survivor.phone = phone
            survivor.phone_normalized = normalized_phone
            merge_result = merge_customers(
                db,
                source=source,
                target=survivor,
                performed_by_staff_id=actor_id,
            )
            customer = survivor
            result = CustomerUpdateResult(
                customer=survivor,
                merge_happened=True,
                merged_from_customer_id=merge_result.source_customer_id,
            )
        else:
            customer.phone = phone
            customer.phone_normalized = normalized_phone

    if "tag_ids" in fields_set:
        _sync_customer_tags(
            db,
            customer_id=customer.id,
            tag_ids=payload.tag_ids or [],
            actor_id=actor_id,
            branch_scope=branch_scope,
        )
    if "preferences" in fields_set:
        _sync_customer_preferences(
            db,
            customer_id=customer.id,
            preferences=payload.preferences or [],
            actor_id=actor_id,
            branch_scope=branch_scope,
        )

    customer.updated_at = datetime.now(UTC)
    db.add(customer)
    db.flush()
    return result


def tag_definition_out(definition: CustomerTagDefinition) -> CustomerTagDefinitionOut:
    return CustomerTagDefinitionOut(
        id=definition.id,
        name=definition.name,
        slug=definition.slug,
        scope=definition.scope,
        branch_id=definition.branch_id,
        is_active=definition.is_active,
    )


def preference_definition_out(
    definition: CustomerPreferenceDefinition,
) -> CustomerPreferenceDefinitionOut:
    return CustomerPreferenceDefinitionOut(
        id=definition.id,
        name=definition.name,
        slug=definition.slug,
        scope=definition.scope,
        branch_id=definition.branch_id,
        value_type=definition.value_type,
        options_json=definition.options_json,
        is_active=definition.is_active,
    )


def create_tag_definition(
    *,
    actor_id: int,
    payload: CustomerTagDefinitionCreate,
    branch_scope: int | None,
) -> CustomerTagDefinition:
    scope = DefinitionScope.branch if branch_scope is not None else payload.scope
    branch_id = branch_scope if scope == DefinitionScope.branch else None
    return CustomerTagDefinition(
        name=payload.name.strip(),
        slug=normalize_slug(payload.slug),
        scope=scope,
        branch_id=branch_id,
        is_active=payload.is_active,
        created_by_staff_id=actor_id,
    )


def update_tag_definition(
    definition: CustomerTagDefinition,
    *,
    payload: CustomerTagDefinitionUpdate,
    branch_scope: int | None,
) -> CustomerTagDefinition:
    fields_set = payload.model_fields_set
    if "name" in fields_set and payload.name is not None:
        definition.name = payload.name.strip()
    if "slug" in fields_set and payload.slug is not None:
        definition.slug = normalize_slug(payload.slug)
    if "is_active" in fields_set and payload.is_active is not None:
        definition.is_active = payload.is_active
    if branch_scope is None:
        if "scope" in fields_set and payload.scope is not None:
            definition.scope = payload.scope
        if definition.scope == DefinitionScope.branch:
            definition.branch_id = payload.branch_id if "branch_id" in fields_set else definition.branch_id
        else:
            definition.branch_id = None
    else:
        definition.scope = DefinitionScope.branch
        definition.branch_id = branch_scope
    definition.updated_at = datetime.now(UTC)
    return definition


def create_preference_definition(
    *,
    actor_id: int,
    payload: CustomerPreferenceDefinitionCreate,
    branch_scope: int | None,
) -> CustomerPreferenceDefinition:
    scope = DefinitionScope.branch if branch_scope is not None else payload.scope
    branch_id = branch_scope if scope == DefinitionScope.branch else None
    return CustomerPreferenceDefinition(
        name=payload.name.strip(),
        slug=normalize_slug(payload.slug),
        scope=scope,
        branch_id=branch_id,
        value_type=payload.value_type,
        options_json=payload.options_json,
        is_active=payload.is_active,
        created_by_staff_id=actor_id,
    )


def update_preference_definition(
    definition: CustomerPreferenceDefinition,
    *,
    payload: CustomerPreferenceDefinitionUpdate,
    branch_scope: int | None,
) -> CustomerPreferenceDefinition:
    fields_set = payload.model_fields_set
    if "name" in fields_set and payload.name is not None:
        definition.name = payload.name.strip()
    if "slug" in fields_set and payload.slug is not None:
        definition.slug = normalize_slug(payload.slug)
    if "value_type" in fields_set and payload.value_type is not None:
        definition.value_type = payload.value_type
    if "options_json" in fields_set:
        definition.options_json = payload.options_json
    if "is_active" in fields_set and payload.is_active is not None:
        definition.is_active = payload.is_active
    if branch_scope is None:
        if "scope" in fields_set and payload.scope is not None:
            definition.scope = payload.scope
        if definition.scope == DefinitionScope.branch:
            definition.branch_id = payload.branch_id if "branch_id" in fields_set else definition.branch_id
        else:
            definition.branch_id = None
    else:
        definition.scope = DefinitionScope.branch
        definition.branch_id = branch_scope
    definition.updated_at = datetime.now(UTC)
    return definition
