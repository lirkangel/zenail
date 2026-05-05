from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import StaffRole


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(sa_column=Column(String(200), nullable=False))
    email: str = Field(sa_column=Column(String(320), nullable=False, unique=True, index=True))
    phone: str | None = Field(default=None, sa_column=Column(String(50)))
    password_hash: str = Field(sa_column=Column(String(500), nullable=False))
    role: StaffRole = Field(sa_column=Column(Enum(StaffRole, name="staff_role"), nullable=False))
    branch_id: int | None = Field(default=None, sa_column=Column(Integer, ForeignKey("branches.id", ondelete="SET NULL")))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    branch: Optional["Branch"] = Relationship()

