from datetime import datetime, time

from sqlalchemy import Column, DateTime, String, Time
from sqlmodel import Field, SQLModel



class Branch(SQLModel, table=True):
    __tablename__ = "branches"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(200), nullable=False))
    address: str | None = Field(default=None, sa_column=Column(String(500)))
    phone: str | None = Field(default=None, sa_column=Column(String(50)))
    timezone: str = Field(default="UTC", sa_column=Column(String(100), nullable=False))
    open_time: time = Field(default=time(9, 0), sa_column=Column(Time, nullable=False))
    close_time: time = Field(default=time(20, 0), sa_column=Column(Time, nullable=False))
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
