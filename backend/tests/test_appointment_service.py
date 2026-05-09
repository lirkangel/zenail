from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationKind,
    Procedure,
    Staff,
)
from app.models.enums import AppointmentStatus, StaffRole
from app.services import appointment_service


def _seed(db: Session) -> Appointment:
    branch = Branch(
        name="B", timezone="Asia/Ho_Chi_Minh", open_time=time(8, 0), close_time=time(20, 0)
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    master = Staff(
        full_name="Linh", email="linh@x", password_hash="x",
        role=StaffRole.master, branch_id=branch.id,
    )
    db.add(master)
    proc = Procedure(name="Manicure", duration_minutes=60, price=Decimal("100000"))
    db.add(proc)
    db.commit()
    db.refresh(master)
    db.refresh(proc)

    appt = Appointment(
        branch_id=branch.id, master_id=master.id, procedure_id=proc.id,
        client_name="A", client_phone="0900", client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        price=Decimal("100000"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def test_cancel_sets_status_and_emits_notifications(db_session: Session) -> None:
    appt = _seed(db_session)
    appointment_service.cancel(appt, db_session)
    db_session.commit()

    db_session.refresh(appt)
    assert appt.status == AppointmentStatus.canceled
    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.canceled)
    ).all()
    assert rows


def test_reschedule_sets_times_and_emits_notifications(db_session: Session) -> None:
    appt = _seed(db_session)
    old_start = appt.start_time
    new_start = old_start + timedelta(days=1)
    new_end = appt.end_time + timedelta(days=1)

    appointment_service.reschedule(appt, new_start=new_start, new_end=new_end, session=db_session)
    db_session.commit()

    db_session.refresh(appt)
    # SQLite may return naive; compare ignoring tz
    stored = appt.start_time
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=timezone.utc)
    expected = new_start
    if expected.tzinfo is None:
        expected = expected.replace(tzinfo=timezone.utc)
    assert abs((stored - expected).total_seconds()) < 1
    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.rescheduled)
    ).all()
    assert rows
