from datetime import datetime, time, timezone
from decimal import Decimal

from sqlmodel import Session

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
)


def _branch(db: Session) -> Branch:
    b = Branch(name="B", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def test_notification_row_roundtrip(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    n = Notification(
        appointment_id=appt.id,
        kind=NotificationKind.canceled,
        recipient_role=NotificationRecipientRole.guest,
        recipient_address="0900",
        channel=NotificationChannel.sms,
        template_key="canceled.guest.sms",
        scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    assert n.id is not None
    assert n.status == NotificationStatus.pending
    assert n.attempt_count == 0
