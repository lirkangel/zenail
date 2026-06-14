from datetime import datetime
from decimal import Decimal

from sqlmodel import SQLModel

from app.models.enums import AppointmentStatus


class CustomerUpdate(SQLModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class CustomerListItemOut(SQLModel):
    id: int
    full_name: str
    phone: str
    email: str | None = None
    notes: str | None = None
    visit_count: int
    completed_spend: Decimal
    latest_visit: datetime | None = None
    upcoming_appointment: datetime | None = None


class CustomerListOut(SQLModel):
    items: list[CustomerListItemOut]
    total: int
    limit: int
    offset: int


class CustomerAppointmentOut(SQLModel):
    id: int
    branch_id: int
    master_id: int
    master_name: str | None = None
    start_time: datetime
    end_time: datetime
    price: Decimal
    status: AppointmentStatus
    procedures: list[str]


class CustomerDetailOut(CustomerListItemOut):
    merge_happened: bool = False
    merged_from_customer_id: int | None = None
    appointments: list[CustomerAppointmentOut]
