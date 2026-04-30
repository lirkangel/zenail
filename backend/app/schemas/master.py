from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AppointmentStatus, RescheduleRequestStatus


class MasterAppointmentOut(BaseModel):
    id: int
    branch_id: int
    procedure_id: int
    client_name: str
    client_phone: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    status: AppointmentStatus


class RescheduleRequestCreate(BaseModel):
    appointment_id: int
    proposed_start_time: datetime
    reason: str | None = None


class RescheduleRequestOut(BaseModel):
    id: int
    appointment_id: int
    master_id: int
    proposed_start_time: datetime
    reason: str | None = None
    status: RescheduleRequestStatus
    created_at: datetime

