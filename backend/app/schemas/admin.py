from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, EmailStr

from app.models.enums import AppointmentStatus, RescheduleRequestStatus, StaffRole


class BranchCreate(BaseModel):
    name: str
    address: str | None = None
    phone: str | None = None
    open_time: time = time(9, 0)
    close_time: time = time(20, 0)


class BranchUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    phone: str | None = None
    open_time: time | None = None
    close_time: time | None = None


class BranchAdminOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None
    open_time: time
    close_time: time


class StaffCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str
    role: StaffRole
    branch_id: int | None = None
    is_active: bool = True


class StaffUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
    role: StaffRole | None = None
    branch_id: int | None = None
    is_active: bool | None = None


class StaffAdminOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: StaffRole
    branch_id: int | None = None
    is_active: bool


class ProcedureCreate(BaseModel):
    name: str
    description: str | None = None
    category: str | None = None
    duration_minutes: int
    price: Decimal
    is_active: bool = True


class ProcedureUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    duration_minutes: int | None = None
    price: Decimal | None = None
    is_active: bool | None = None


class ProcedureAdminOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    duration_minutes: int
    price: Decimal
    is_active: bool


class BranchNonWorkingDayCreate(BaseModel):
    day: date
    reason: str | None = None


class BranchNonWorkingDayOut(BaseModel):
    id: int
    branch_id: int
    day: date
    reason: str | None = None


class MasterProcedureLink(BaseModel):
    master_id: int
    procedure_id: int


class AdminAppointmentOut(BaseModel):
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


class AdminRescheduleRequestOut(BaseModel):
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


class RevenueBreakdownRow(BaseModel):
    branch_id: int
    total: Decimal


class RevenueBreakdownOut(BaseModel):
    from_date: str
    to_date: str
    total: Decimal
    by_branch: list[RevenueBreakdownRow]

