from datetime import datetime
from decimal import Decimal

from sqlmodel import Field, SQLModel

from app.models.customer import DefinitionScope, PreferenceValueType
from app.models.enums import AppointmentStatus


class CustomerPreferenceValueIn(SQLModel):
    definition_id: int
    value_text: str | None = None
    value_bool: bool | None = None
    value_option: str | None = None


class CustomerUpdate(SQLModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    tag_ids: list[int] | None = None
    preferences: list[CustomerPreferenceValueIn] | None = None


class CustomerTagOut(SQLModel):
    id: int
    name: str
    slug: str
    scope: DefinitionScope
    branch_id: int | None = None


class CustomerPreferenceOut(SQLModel):
    definition_id: int
    name: str
    slug: str
    scope: DefinitionScope
    branch_id: int | None = None
    value_type: PreferenceValueType
    value_text: str | None = None
    value_bool: bool | None = None
    value_option: str | None = None


class CustomerTagDefinitionCreate(SQLModel):
    name: str
    slug: str
    scope: DefinitionScope = DefinitionScope.global_
    branch_id: int | None = None
    is_active: bool = True


class CustomerTagDefinitionUpdate(SQLModel):
    name: str | None = None
    slug: str | None = None
    scope: DefinitionScope | None = None
    branch_id: int | None = None
    is_active: bool | None = None


class CustomerTagDefinitionOut(SQLModel):
    id: int
    name: str
    slug: str
    scope: DefinitionScope
    branch_id: int | None = None
    is_active: bool


class CustomerPreferenceDefinitionCreate(SQLModel):
    name: str
    slug: str
    scope: DefinitionScope = DefinitionScope.global_
    branch_id: int | None = None
    value_type: PreferenceValueType
    options_json: list[str] | None = None
    is_active: bool = True


class CustomerPreferenceDefinitionUpdate(SQLModel):
    name: str | None = None
    slug: str | None = None
    scope: DefinitionScope | None = None
    branch_id: int | None = None
    value_type: PreferenceValueType | None = None
    options_json: list[str] | None = None
    is_active: bool | None = None


class CustomerPreferenceDefinitionOut(SQLModel):
    id: int
    name: str
    slug: str
    scope: DefinitionScope
    branch_id: int | None = None
    value_type: PreferenceValueType
    options_json: list[str] | None = None
    is_active: bool


class CustomerListItemOut(SQLModel):
    id: int
    full_name: str
    phone: str
    email: str | None = None
    notes: str | None = None
    tags: list[CustomerTagOut] = Field(default_factory=list)
    preferences: list[CustomerPreferenceOut] = Field(default_factory=list)
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
