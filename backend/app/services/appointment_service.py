from __future__ import annotations

from datetime import datetime

from sqlmodel import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.services import notifications as notif_service


def cancel(appointment: Appointment, session: Session) -> None:
    if appointment.status != AppointmentStatus.canceled:
        appointment.status = AppointmentStatus.canceled
        session.add(appointment)
    notif_service.on_canceled(appointment, session)


def reschedule(
    appointment: Appointment,
    *,
    new_start: datetime,
    new_end: datetime,
    session: Session,
) -> None:
    old_start = appointment.start_time
    appointment.start_time = new_start
    appointment.end_time = new_end
    session.add(appointment)
    notif_service.on_rescheduled(appointment, old_start, session)
