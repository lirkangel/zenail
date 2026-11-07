from sqlalchemy.orm import object_session

from app.models.appointment import Appointment
from app.schemas.public import (
    AppointmentCustomerSummaryOut,
    AppointmentOut,
    AppointmentProcedureOut,
    StaffAppointmentOut,
)
from app.services.customers import customer_preferences_out, customer_tags_out


def _procedures_out(appt: Appointment) -> list[AppointmentProcedureOut]:
    snapshots = list(appt.procedures)
    if snapshots:
        return [
            AppointmentProcedureOut(
                id=p.procedure_id,
                name=p.name_snapshot,
                duration_minutes=p.duration_minutes_snapshot,
                price=p.price_snapshot,
            )
            for p in snapshots
        ]
    return [
        AppointmentProcedureOut(
            id=appt.procedure_id,
            name=appt.procedure.name if appt.procedure else "Procedure",
            duration_minutes=appt.procedure.duration_minutes if appt.procedure else 0,
            price=appt.price,
        )
    ]


def appointment_to_out(appt: Appointment) -> AppointmentOut:
    """Appointment payload safe for guests: no internal CRM data."""
    procedures = _procedures_out(appt)
    return AppointmentOut(
        id=appt.id,
        booking_reference=appt.booking_reference,
        branch_id=appt.branch_id,
        master_id=appt.master_id,
        customer_id=appt.customer_id,
        master_name=appt.master.full_name if appt.master else None,
        procedure_id=appt.procedure_id,
        procedure_ids=[p.id for p in procedures],
        procedures=procedures,
        client_name=appt.client_name,
        client_phone=appt.client_phone,
        client_email=appt.client_email,
        start_time=appt.start_time,
        end_time=appt.end_time,
        total_duration_minutes=sum(p.duration_minutes for p in procedures),
        price=appt.price,
        status=appt.status,
    )


def appointment_to_staff_out(appt: Appointment) -> StaffAppointmentOut:
    """Appointment payload for staff routes, hydrated with CRM context.

    Call only after the route's role/branch authorization checks.
    """
    out = StaffAppointmentOut(**appointment_to_out(appt).model_dump())
    session = object_session(appt)
    if appt.customer and session is not None:
        out.customer_summary = AppointmentCustomerSummaryOut(
            id=appt.customer.id,
            full_name=appt.customer.full_name,
            phone=appt.customer.phone,
            email=appt.customer.email,
            notes=appt.customer.notes,
        )
        out.customer_tags = customer_tags_out(session, customer_id=appt.customer.id, branch_id=appt.branch_id)
        out.customer_preferences = customer_preferences_out(
            session, customer_id=appt.customer.id, branch_id=appt.branch_id
        )
    return out
