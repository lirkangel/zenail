from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select as sa_select
from sqlmodel import Session

from app.models.appointment import Appointment
from app.models.appointment_procedure import AppointmentProcedure
from app.models.branch import Branch
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
)
from app.models.enums import StaffRole
from app.models.procedure import Procedure
from app.models.staff import Staff


UTC = timezone.utc

_CHANNELS: dict[
    tuple[NotificationKind, NotificationRecipientRole], list[NotificationChannel]
] = {
    (NotificationKind.reminder_24h, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.canceled, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.canceled, NotificationRecipientRole.master): [NotificationChannel.email],
    (NotificationKind.canceled, NotificationRecipientRole.manager): [NotificationChannel.email],
    (NotificationKind.rescheduled, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.rescheduled, NotificationRecipientRole.master): [NotificationChannel.email],
}


def _format_local(dt: datetime, branch: Branch) -> str:
    from zoneinfo import ZoneInfo

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo(branch.timezone)).strftime("%H:%M %d/%m/%Y")


def _build_payload(
    *,
    appointment: Appointment,
    branch: Branch,
    master: Staff | None,
    procedures: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_name": appointment.client_name,
        "branch_name": branch.name,
        "master_name": master.full_name if master else "",
        "procedures": procedures,
        "start_local": _format_local(appointment.start_time, branch),
        "booking_reference": appointment.booking_reference,
    }
    if extra:
        payload.update(extra)
    return payload


def _resolve_guest_address(channel: NotificationChannel, appt: Appointment) -> str | None:
    if channel == NotificationChannel.email:
        return appt.client_email or None
    return appt.client_phone or None


def _resolve_master_address(master: Staff | None) -> str | None:
    return master.email if master and master.email else None


def _resolve_managers(session: Session, branch_id: int) -> list[Staff]:
    return list(
        session.scalars(
            sa_select(Staff).where(
                Staff.role == StaffRole.manager,
                Staff.branch_id == branch_id,
                Staff.is_active.is_(True),
            )
        ).all()
    )


def _load_context(session: Session, appt: Appointment) -> tuple[Branch, Staff | None, list[str]]:
    branch = session.get(Branch, appt.branch_id)
    master = session.get(Staff, appt.master_id)
    procedure_names: list[str] = []
    rows = session.scalars(
        sa_select(AppointmentProcedure).where(AppointmentProcedure.appointment_id == appt.id)
    ).all()
    for r in rows:
        if r.name_snapshot:
            procedure_names.append(r.name_snapshot)
    if not procedure_names and appt.procedure_id:
        proc = session.get(Procedure, appt.procedure_id)
        if proc:
            procedure_names = [proc.name]
    return branch, master, procedure_names


def _insert_row(
    session: Session,
    *,
    appt: Appointment,
    kind: NotificationKind,
    role: NotificationRecipientRole,
    channel: NotificationChannel,
    address: str | None,
    payload: dict[str, Any],
    scheduled_at: datetime,
) -> Notification:
    template_key = f"{kind.value}.{role.value}.{channel.value}"
    if not address:
        n = Notification(
            appointment_id=appt.id,
            kind=kind,
            recipient_role=role,
            recipient_address="",
            channel=channel,
            template_key=template_key,
            payload_json=payload,
            status=NotificationStatus.skipped,
            scheduled_at=scheduled_at,
            last_error=f"no {channel.value} address available",
        )
    else:
        n = Notification(
            appointment_id=appt.id,
            kind=kind,
            recipient_role=role,
            recipient_address=address,
            channel=channel,
            template_key=template_key,
            payload_json=payload,
            status=NotificationStatus.pending,
            scheduled_at=scheduled_at,
        )
    session.add(n)
    return n


def _supersede_pending(session: Session, appointment_id: int, reason: str) -> None:
    pending = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment_id,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending:
        row.status = NotificationStatus.skipped
        row.last_error = reason
        session.add(row)


def on_canceled(appointment: Appointment, session: Session) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures
    )
    _supersede_pending(session, appointment.id, "superseded by cancel")

    now = datetime.now(UTC)
    out: list[Notification] = []

    for channel in _CHANNELS[(NotificationKind.canceled, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.canceled,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=now,
            )
        )

    out.append(
        _insert_row(
            session,
            appt=appointment,
            kind=NotificationKind.canceled,
            role=NotificationRecipientRole.master,
            channel=NotificationChannel.email,
            address=_resolve_master_address(master),
            payload=payload,
            scheduled_at=now,
        )
    )

    for mgr in _resolve_managers(session, appointment.branch_id):
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.canceled,
                role=NotificationRecipientRole.manager,
                channel=NotificationChannel.email,
                address=mgr.email,
                payload=payload,
                scheduled_at=now,
            )
        )
    return out


def on_rescheduled(
    appointment: Appointment, old_start: datetime, session: Session
) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    extra = {"old_start_local": _format_local(old_start, branch)}
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures, extra=extra
    )

    pending_reminders = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment.id,
            Notification.kind == NotificationKind.reminder_24h,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending_reminders:
        session.delete(row)

    pending_resched = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment.id,
            Notification.kind == NotificationKind.rescheduled,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending_resched:
        row.status = NotificationStatus.skipped
        row.last_error = "superseded by newer reschedule"

    now = datetime.now(UTC)
    out: list[Notification] = []

    for channel in _CHANNELS[(NotificationKind.rescheduled, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.rescheduled,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=now,
            )
        )

    out.append(
        _insert_row(
            session,
            appt=appointment,
            kind=NotificationKind.rescheduled,
            role=NotificationRecipientRole.master,
            channel=NotificationChannel.email,
            address=_resolve_master_address(master),
            payload=payload,
            scheduled_at=now,
        )
    )

    out.extend(enqueue_reminder(appointment, session))
    return out


def enqueue_reminder(appointment: Appointment, session: Session) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures
    )
    start = appointment.start_time
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    target = start - timedelta(hours=24)
    now = datetime.now(UTC)
    scheduled_at = max(target, now)

    out: list[Notification] = []
    for channel in _CHANNELS[(NotificationKind.reminder_24h, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.reminder_24h,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=scheduled_at,
            )
        )
    return out
