from datetime import date, datetime, time
from decimal import Decimal

from pydantic import EmailStr
from sqlmodel import SQLModel

from app.models.enums import AppointmentStatus, RescheduleRequestStatus, StaffRole


class BranchCreate(SQLModel):
    name: str
    address: str | None = None
    phone: str | None = None
    timezone: str = "UTC"
    open_time: time = time(9, 0)
    close_time: time = time(20, 0)


class BranchUpdate(SQLModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    timezone: str | None = None
    open_time: time | None = None
    close_time: time | None = None


class BranchAdminOut(SQLModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None
    timezone: str
    open_time: time
    close_time: time
    currency_code: str


class StaffCreate(SQLModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: StaffRole
    branch_id: int | None = None
    is_active: bool = True


class StaffUpdate(SQLModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: StaffRole | None = None
    branch_id: int | None = None
    is_active: bool | None = None


class StaffAdminOut(SQLModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    role: StaffRole
    branch_id: int | None = None
    is_active: bool


class ProcedureCreate(SQLModel):
    name: str
    description: str | None = None
    category: str | None = None
    duration_minutes: int
    price: Decimal
    is_active: bool = True


class ProcedureUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    duration_minutes: int | None = None
    price: Decimal | None = None
    is_active: bool | None = None


class ProcedureAdminOut(SQLModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    duration_minutes: int
    price: Decimal
    is_active: bool


class BranchNonWorkingDayCreate(SQLModel):
    day: date
    reason: str | None = None


class BranchNonWorkingDayOut(SQLModel):
    id: int
    branch_id: int
    day: date
    reason: str | None = None


class MasterProcedureLink(SQLModel):
    master_id: int
    procedure_id: int


class AdminAppointmentOut(SQLModel):
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
    status: AppointmentStatus | None = None


class AdminRescheduleRequestOut(SQLModel):
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


class RevenueBreakdownRow(SQLModel):
    branch_id: int
    total: Decimal


class RevenueBreakdownOut(SQLModel):
    from_date: str
    to_date: str
    total: Decimal
    by_branch: list[RevenueBreakdownRow]
