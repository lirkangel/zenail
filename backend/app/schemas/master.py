from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.models.enums import AppointmentStatus, RescheduleRequestStatus


class MasterAppointmentOut(SQLModel):
    id: int
    branch_id: int
    procedure_id: int
    client_name: str
    client_phone: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    status: AppointmentStatus


class RescheduleRequestCreate(SQLModel):
    appointment_id: int
    proposed_start_time: datetime
    reason: str | None = None


class RescheduleRequestOut(SQLModel):
    id: int
    appointment_id: int
    master_id: int
    proposed_start_time: datetime
    reason: str | None = None
    status: RescheduleRequestStatus
    created_at: datetime

