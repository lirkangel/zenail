from datetime import datetime
from decimal import Decimal
import secrets
from typing import List, Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import AppointmentStatus


def generate_booking_reference() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"

    id: int | None = Field(default=None, primary_key=True)

    branch_id: int = Field(sa_column=Column(Integer, ForeignKey("branches.id", ondelete="RESTRICT"), index=True))
    master_id: int = Field(sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), index=True))
    procedure_id: int = Field(sa_column=Column(Integer, ForeignKey("procedures.id", ondelete="RESTRICT")))

    client_name: str = Field(sa_column=Column(String(200), nullable=False))
    client_phone: str = Field(sa_column=Column(String(50), nullable=False))
    booking_reference: str = Field(
        default_factory=generate_booking_reference,
        sa_column=Column(String(32), nullable=False, unique=True, index=True),
    )

    start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    end_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))

    price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    status: AppointmentStatus = Field(
        default=AppointmentStatus.scheduled,
        sa_column=Column(Enum(AppointmentStatus, name="appointment_status"), nullable=False),
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow),
    )

    branch: Optional["Branch"] = Relationship()
    master: Optional["Staff"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[Appointment.master_id]"})
    procedure: Optional["Procedure"] = Relationship()
    procedures: List["AppointmentProcedure"] = Relationship(
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "AppointmentProcedure.sort_order"}
    )
