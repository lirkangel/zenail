from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import AppointmentStatus


class BranchOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None
    timezone: str
    open_time: time
    close_time: time


class MasterOut(BaseModel):
    id: int
    full_name: str


class ProcedureOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    category: str | None = None
    duration_minutes: int
    price: Decimal


class AvailabilityOut(BaseModel):
    master_id: int
    procedure_id: int | None = None
    procedure_ids: list[int]
    date: str
    branch_timezone: str
    total_duration_minutes: int
    total_price: Decimal
    slots: list[datetime]


class AppointmentCreate(BaseModel):
    branch_id: int
    master_id: int
    procedure_id: int | None = None
    procedure_ids: list[int] = Field(default_factory=list)
    client_name: str
    client_phone: str
    start_time: datetime


class AppointmentProcedureOut(BaseModel):
    id: int
    name: str
    duration_minutes: int
    price: Decimal


class AppointmentOut(BaseModel):
    id: int
    booking_reference: str
    branch_id: int
    master_id: int
    master_name: str | None = None
    procedure_id: int
    procedure_ids: list[int]
    procedures: list[AppointmentProcedureOut]
    client_name: str
    client_phone: str
    start_time: datetime
    end_time: datetime
    total_duration_minutes: int
    price: Decimal
    status: AppointmentStatus
