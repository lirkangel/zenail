from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AppointmentStatus, RescheduleRequestStatus


class ManagerAppointmentOut(BaseModel):
    id: int
    branch_id: int
    master_id: int
    procedure_id: int
    client_name: str
    client_phone: str
    start_time: datetime
    end_time: datetime
    price: Decimal
    status: AppointmentStatus


class AppointmentUpdate(BaseModel):
    start_time: datetime | None = None
    status: AppointmentStatus | None = None


class ManagerMasterOut(BaseModel):
    id: int
    full_name: str
    branch_id: int | None


class MasterReassign(BaseModel):
    branch_id: int | None


class ManagerRescheduleRequestOut(BaseModel):
    id: int
    appointment_id: int
    master_id: int
    proposed_start_time: datetime
    reason: str | None = None
    status: RescheduleRequestStatus
    created_at: datetime
    decided_by_manager_id: int | None = None
    decided_at: datetime | None = None


class RescheduleRequestDecision(BaseModel):
    status: RescheduleRequestStatus


class RevenueOut(BaseModel):
    from_date: str
    to_date: str
    total: Decimal

