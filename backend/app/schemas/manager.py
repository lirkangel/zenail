from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.models.enums import AppointmentStatus, RescheduleRequestStatus


class ManagerAppointmentOut(SQLModel):
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


class AppointmentUpdate(SQLModel):
    start_time: datetime | None = None
    master_id: int | None = None
    status: AppointmentStatus | None = None


class ManagerMasterOut(SQLModel):
    id: int
    full_name: str
    branch_id: int | None


class MasterReassign(SQLModel):
    branch_id: int | None


class ManagerRescheduleRequestOut(SQLModel):
    id: int
    appointment_id: int
    master_id: int
    proposed_start_time: datetime
    reason: str | None = None
    status: RescheduleRequestStatus
    created_at: datetime
    decided_by_manager_id: int | None = None
    decided_at: datetime | None = None


class RescheduleRequestDecision(SQLModel):
    status: RescheduleRequestStatus


class RevenueOut(SQLModel):
    from_date: str
    to_date: str
    total: Decimal

