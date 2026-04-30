from datetime import datetime, time
from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import AppointmentStatus


class BranchOut(BaseModel):
    id: int
    name: str
    address: str | None = None
    phone: str | None = None
    open_time: time
    close_time: time


class MasterOut(BaseModel):
    id: int
    full_name: str


class ProcedureOut(BaseModel):
    id: int
    name: str
    duration_minutes: int
    price: Decimal


class AvailabilityOut(BaseModel):
    master_id: int
    procedure_id: int
    date: str
    slots: list[datetime]


class AppointmentCreate(BaseModel):
    branch_id: int
    master_id: int
    procedure_id: int
    client_name: str
    client_phone: str
    start_time: datetime


class AppointmentOut(BaseModel):
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

