from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlmodel import Field, SQLModel



class AppointmentProcedure(SQLModel, table=True):
    __tablename__ = "appointment_procedures"

    appointment_id: int = Field(
        sa_column=Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), primary_key=True)
    )
    procedure_id: int = Field(
        sa_column=Column(Integer, ForeignKey("procedures.id", ondelete="RESTRICT"), primary_key=True)
    )
    sort_order: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    name_snapshot: str = Field(sa_column=Column(String(200), nullable=False))
    duration_minutes_snapshot: int = Field(sa_column=Column(Integer, nullable=False))
    price_snapshot: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

