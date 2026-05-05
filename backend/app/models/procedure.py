from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlmodel import Field, SQLModel



class Procedure(SQLModel, table=True):
    __tablename__ = "procedures"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(String(1000)))
    category: str | None = Field(default=None, sa_column=Column(String(100)))
    duration_minutes: int = Field(sa_column=Column(Integer, nullable=False))
    price: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

