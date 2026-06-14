from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import Appointment
from app.models.customer import Customer, CustomerMergeLog, CustomerPreferenceValue, CustomerTag

UTC = timezone.utc


@dataclass
class CustomerMergeResult:
    source_customer_id: int
    target_customer_id: int


def _combine_notes(primary: str | None, secondary: str | None) -> str | None:
    parts = [part.strip() for part in [primary, secondary] if part and part.strip()]
    if not parts:
        return None
    deduped: list[str] = []
    for part in parts:
        if part not in deduped:
            deduped.append(part)
    return "\n\n".join(deduped)


def _move_appointments(db: Session, *, source_id: int, target_id: int) -> None:
    appointments = db.exec(select(Appointment).where(Appointment.customer_id == source_id)).all()
    for appointment in appointments:
        appointment.customer_id = target_id
        db.add(appointment)


def _move_tags(db: Session, *, source_id: int, target_id: int) -> None:
    tags = db.exec(select(CustomerTag).where(CustomerTag.customer_id == source_id)).all()
    for tag in tags:
        existing = db.get(CustomerTag, (target_id, tag.tag_definition_id))
        if existing is None:
            db.add(
                CustomerTag(
                    customer_id=target_id,
                    tag_definition_id=tag.tag_definition_id,
                    assigned_by_staff_id=tag.assigned_by_staff_id,
                    created_at=tag.created_at,
                )
            )
        db.delete(tag)


def _move_preference_values(db: Session, *, source_id: int, target_id: int) -> None:
    preferences = db.exec(
        select(CustomerPreferenceValue).where(CustomerPreferenceValue.customer_id == source_id)
    ).all()
    for preference in preferences:
        existing = db.get(CustomerPreferenceValue, (target_id, preference.preference_definition_id))
        if existing is None:
            db.add(
                CustomerPreferenceValue(
                    customer_id=target_id,
                    preference_definition_id=preference.preference_definition_id,
                    value_text=preference.value_text,
                    value_bool=preference.value_bool,
                    value_option=preference.value_option,
                    updated_by_staff_id=preference.updated_by_staff_id,
                    created_at=preference.created_at,
                    updated_at=preference.updated_at,
                )
            )
        db.delete(preference)


def merge_customers(
    db: Session,
    *,
    source: Customer,
    target: Customer,
    performed_by_staff_id: int,
) -> CustomerMergeResult:
    now = datetime.now(UTC)

    _move_appointments(db, source_id=source.id, target_id=target.id)
    _move_tags(db, source_id=source.id, target_id=target.id)
    _move_preference_values(db, source_id=source.id, target_id=target.id)

    target.notes = _combine_notes(target.notes, source.notes)
    target.updated_at = now
    source.is_active = False
    source.merged_into_customer_id = target.id
    source.updated_at = now

    db.add(target)
    db.add(source)
    db.add(
        CustomerMergeLog(
            source_customer_id=source.id,
            target_customer_id=target.id,
            performed_by_staff_id=performed_by_staff_id,
            summary_json={
                "source_phone": source.phone_normalized,
                "target_phone": target.phone_normalized,
            },
            created_at=now,
        )
    )
    db.flush()
    return CustomerMergeResult(source_customer_id=source.id, target_customer_id=target.id)
