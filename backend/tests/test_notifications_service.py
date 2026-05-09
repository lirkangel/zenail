from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
    Procedure,
    Staff,
)
from app.models.enums import StaffRole
from app.services import notifications as notif_service


def _seed(db: Session, *, client_email=None, with_manager=True):
    branch = Branch(
        name="Zenail Central",
        timezone="Asia/Ho_Chi_Minh",
        open_time=time(8, 0),
        close_time=time(20, 0),
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    master = Staff(
        full_name="Linh",
        email="linh@zenail.local",
        password_hash="x",
        role=StaffRole.master,
        branch_id=branch.id,
    )
    db.add(master)
    if with_manager:
        db.add(Staff(
            full_name="Mgr",
            email="mgr@zenail.local",
            password_hash="x",
            role=StaffRole.manager,
            branch_id=branch.id,
        ))
    db.commit()
    db.refresh(master)

    proc = Procedure(name="Manicure", duration_minutes=60, price=Decimal("100000"))
    db.add(proc)
    db.commit()
    db.refresh(proc)

    appt = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        client_name="An",
        client_phone="0900000000",
        client_email=client_email,
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        price=Decimal("100000"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def _make_aware(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def test_on_canceled_with_email_creates_full_row_set(db_session):
    appt = _seed(db_session, client_email="an@example.com")
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(select(Notification)).all()
    by_role = {(r.recipient_role, r.channel) for r in rows}
    assert (NotificationRecipientRole.guest, NotificationChannel.email) in by_role
    assert (NotificationRecipientRole.guest, NotificationChannel.sms) in by_role
    assert (NotificationRecipientRole.guest, NotificationChannel.zalo_zns) in by_role
    assert (NotificationRecipientRole.master, NotificationChannel.email) in by_role
    assert (NotificationRecipientRole.manager, NotificationChannel.email) in by_role
    assert {r.kind for r in rows} == {NotificationKind.canceled}
    assert all(r.status == NotificationStatus.pending for r in rows)


def test_on_canceled_without_email_skips_guest_email(db_session):
    appt = _seed(db_session, client_email=None)
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(
            Notification.recipient_role == NotificationRecipientRole.guest,
            Notification.channel == NotificationChannel.email,
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].status == NotificationStatus.skipped
    assert "no email" in (rows[0].last_error or "")


def test_on_canceled_without_manager_writes_no_manager_row(db_session):
    appt = _seed(db_session, client_email="an@example.com", with_manager=False)
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(Notification.recipient_role == NotificationRecipientRole.manager)
    ).all()
    assert rows == []


def test_on_canceled_marks_existing_pending_as_skipped(db_session):
    appt = _seed(db_session, client_email="an@example.com")
    notif_service.enqueue_reminder(appt, db_session)
    db_session.commit()

    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    reminder_rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert reminder_rows
    assert all(r.status == NotificationStatus.skipped for r in reminder_rows)


def test_on_rescheduled_replaces_pending_reminder(db_session):
    appt = _seed(db_session, client_email="an@example.com")
    notif_service.enqueue_reminder(appt, db_session)
    db_session.commit()

    old_start = appt.start_time
    appt.start_time = appt.start_time + timedelta(days=1)
    appt.end_time = appt.end_time + timedelta(days=1)
    db_session.add(appt)
    db_session.commit()

    notif_service.on_rescheduled(appt, old_start, db_session)
    db_session.commit()

    reminders = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert all(r.status == NotificationStatus.pending for r in reminders)
    expected_scheduled = _make_aware(appt.start_time) - timedelta(hours=24)
    for r in reminders:
        assert abs((_make_aware(r.scheduled_at) - expected_scheduled).total_seconds()) < 5


def test_on_rescheduled_within_24h_schedules_now(db_session):
    appt = _seed(db_session, client_email="an@example.com")
    appt.start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    appt.end_time = appt.start_time + timedelta(hours=1)
    db_session.add(appt)
    db_session.commit()

    old_start = appt.start_time + timedelta(hours=1)
    notif_service.on_rescheduled(appt, old_start, db_session)
    db_session.commit()

    reminders = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert reminders
    now = datetime.now(timezone.utc)
    for r in reminders:
        assert _make_aware(r.scheduled_at) <= now + timedelta(seconds=5)


def test_master_without_email_is_skipped(db_session):
    appt = _seed(db_session, client_email="an@example.com")
    master = db_session.get(Staff, appt.master_id)
    master.email = ""
    db_session.add(master)
    db_session.commit()

    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(Notification.recipient_role == NotificationRecipientRole.master)
    ).all()
    assert len(rows) == 1
    assert rows[0].status == NotificationStatus.skipped
