import asyncio
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
)
from app.models.enums import AppointmentStatus
from app.notifications import scheduler as sched
from app.notifications.providers.base import (
    NotificationProvider,
    ProviderPermanentError,
    ProviderResult,
    ProviderTransientError,
)


class _OkProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        return ProviderResult(ok=True)


class _TransientProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        raise ProviderTransientError("boom")


class _PermanentProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        raise ProviderPermanentError("dead")


def _branch(db: Session) -> Branch:
    b = Branch(name="B", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _make_pending(db: Session, *, scheduled_at: datetime) -> Notification:
    branch = _branch(db)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        price=Decimal("0"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    n = Notification(
        appointment_id=appt.id,
        kind=NotificationKind.canceled,
        recipient_role=NotificationRecipientRole.guest,
        recipient_address="x@example.com",
        channel=NotificationChannel.email,
        template_key="canceled.guest.email",
        payload_json={
            "client_name": "A",
            "branch_name": "B",
            "master_name": "M",
            "procedures": [],
            "start_local": "now",
            "booking_reference": "REF",
        },
        scheduled_at=scheduled_at,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def _make_aware(dt):
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def test_dispatcher_marks_sent_on_success(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _OkProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.sent
    assert n.sent_at is not None


def test_dispatcher_skips_future_rows(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _OkProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.pending


def test_dispatcher_transient_error_increments_attempt(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _TransientProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.pending
    assert n.attempt_count == 1
    assert _make_aware(n.scheduled_at) > datetime.now(timezone.utc)
    assert "boom" in (n.last_error or "")


def test_dispatcher_permanent_error_marks_failed(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _PermanentProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.failed
    assert n.attempt_count == 1


def test_dispatcher_three_transient_failures_marks_failed(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _TransientProvider())

    for _ in range(3):
        db_session.refresh(n)
        n.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db_session.add(n)
        db_session.commit()
        asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.failed
    assert n.attempt_count == 3


def test_enqueue_reminders_creates_rows_inside_window(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert len(rows) == 3  # email + sms + zns


def test_enqueue_reminders_idempotent(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()

    sched.enqueue_reminders(session_factory=lambda: db_session)
    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert len(rows) == 3


def test_enqueue_reminders_skips_canceled_appointment(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
        status=AppointmentStatus.canceled,
    )
    db_session.add(appt)
    db_session.commit()

    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(select(Notification)).all()
    assert rows == []
