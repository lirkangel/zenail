from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from app.db.sqlmodel import session_scope
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.notification import (
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.notifications.providers.base import (
    ProviderPermanentError,
    ProviderTransientError,
)
from app.notifications.registry import get_provider
from app.notifications.templates import render
from app.core.config import settings


_logger = logging.getLogger("zenail.notifications")
UTC = timezone.utc

_BACKOFF = [timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15)]
_MAX_ATTEMPTS = 3
_BATCH = 100


SessionFactory = Callable[[], Session]


def _is_postgres(session: Session) -> bool:
    try:
        return session.bind.dialect.name == "postgresql"
    except AttributeError:
        return False


def _select_pending(session: Session) -> list[Notification]:
    now = datetime.now(UTC)
    stmt = (
        select(Notification)
        .where(
            Notification.status == NotificationStatus.pending,
            Notification.scheduled_at <= now,
            Notification.attempt_count < _MAX_ATTEMPTS,
        )
        .order_by(Notification.scheduled_at)
        .limit(_BATCH)
    )
    if _is_postgres(session):
        stmt = stmt.with_for_update(skip_locked=True)
    return list(session.scalars(stmt).all())


async def dispatch_pending(*, session_factory: SessionFactory | None = None) -> dict:
    factory = session_factory or session_scope
    counts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}

    if session_factory is None:
        with factory() as session:  # type: ignore[attr-defined]
            counts.update(await _dispatch_with_session(session))
    else:
        session = factory()
        counts.update(await _dispatch_with_session(session))
    return counts


async def _dispatch_with_session(session: Session) -> dict:
    counts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    rows = _select_pending(session)
    for row in rows:
        counts["processed"] += 1
        try:
            subject, body = render(row.template_key, settings.notification_default_lang, row.payload_json)
        except Exception as exc:
            row.status = NotificationStatus.failed
            row.last_error = f"template error: {exc}"
            row.attempt_count += 1
            session.add(row)
            counts["failed"] += 1
            session.commit()
            continue

        provider = get_provider(row.channel)
        try:
            result = await provider.send(row, body, subject=subject)
            if result.ok:
                row.status = NotificationStatus.sent
                row.sent_at = datetime.now(UTC)
                row.attempt_count += 1
                counts["sent"] += 1
            else:
                _apply_transient(row)
                row.last_error = result.detail or "provider returned not-ok"
        except ProviderPermanentError as exc:
            row.status = NotificationStatus.failed
            row.attempt_count += 1
            row.last_error = str(exc)
            counts["failed"] += 1
        except ProviderTransientError as exc:
            _apply_transient(row)
            row.last_error = str(exc)
            if row.status == NotificationStatus.failed:
                counts["failed"] += 1
        except Exception as exc:
            _apply_transient(row)
            row.last_error = f"unexpected: {exc}"
            if row.status == NotificationStatus.failed:
                counts["failed"] += 1

        session.add(row)
        session.commit()

        _logger.info(
            "notification.dispatched id=%s kind=%s channel=%s status=%s attempt=%s error=%s",
            row.id, row.kind.value, row.channel.value, row.status.value,
            row.attempt_count, row.last_error,
        )
    return counts


def _apply_transient(row: Notification) -> None:
    row.attempt_count += 1
    if row.attempt_count >= _MAX_ATTEMPTS:
        row.status = NotificationStatus.failed
    else:
        delay = _BACKOFF[min(row.attempt_count - 1, len(_BACKOFF) - 1)]
        row.scheduled_at = datetime.now(UTC) + delay
        row.status = NotificationStatus.pending


def enqueue_reminders(*, session_factory: SessionFactory | None = None) -> int:
    factory = session_factory or session_scope
    if session_factory is None:
        with factory() as session:  # type: ignore[attr-defined]
            return _enqueue_with_session(session)
    return _enqueue_with_session(factory())


def _enqueue_with_session(session: Session) -> int:
    from app.services.notifications import enqueue_reminder

    now = datetime.now(UTC)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=24)

    candidates = list(
        session.scalars(
            select(Appointment).where(
                Appointment.status == AppointmentStatus.scheduled,
                Appointment.start_time >= window_start,
                Appointment.start_time <= window_end,
            )
        ).all()
    )

    inserted = 0
    for appt in candidates:
        existing = session.scalar(
            select(Notification).where(
                Notification.appointment_id == appt.id,
                Notification.kind == NotificationKind.reminder_24h,
            )
        )
        if existing is not None:
            continue
        rows = enqueue_reminder(appt, session)
        inserted += len(rows)
    session.commit()
    return inserted
