from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(sa_column=Column(String(200), nullable=False))
    phone: str = Field(sa_column=Column(String(50), nullable=False))
    phone_normalized: str = Field(sa_column=Column(String(50), nullable=False, unique=True, index=True))
    email: str | None = Field(default=None, sa_column=Column(String(200), nullable=True, index=True))
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )
