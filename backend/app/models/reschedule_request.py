from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import RescheduleRequestStatus


class RescheduleRequest(SQLModel, table=True):
    __tablename__ = "reschedule_requests"

    id: int | None = Field(default=None, primary_key=True)
    appointment_id: int = Field(sa_column=Column(Integer, ForeignKey("appointments.id", ondelete="CASCADE"), index=True))
    master_id: int = Field(sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), index=True))

    proposed_start_time: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    reason: str | None = Field(default=None, sa_column=Column(String(1000)))

    status: RescheduleRequestStatus = Field(
        default=RescheduleRequestStatus.pending,
        sa_column=Column(Enum(RescheduleRequestStatus, name="reschedule_request_status"), nullable=False),
    )

    decided_by_manager_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="SET NULL")),
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    decided_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    appointment: Optional["Appointment"] = Relationship()
    master: Optional["Staff"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[RescheduleRequest.master_id]"})
    decided_by_manager: Optional["Staff"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[RescheduleRequest.decided_by_manager_id]"}
    )

