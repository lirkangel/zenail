from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RescheduleRequestStatus


class RescheduleRequest(Base):
    __tablename__ = "reschedule_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    appointment_id: Mapped[int] = mapped_column(ForeignKey("appointments.id", ondelete="CASCADE"), index=True)
    master_id: Mapped[int] = mapped_column(ForeignKey("staff.id", ondelete="RESTRICT"), index=True)

    proposed_start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000))

    status: Mapped[RescheduleRequestStatus] = mapped_column(
        Enum(RescheduleRequestStatus, name="reschedule_request_status"),
        nullable=False,
        default=RescheduleRequestStatus.pending,
    )

    decided_by_manager_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    appointment = relationship("Appointment")
    master = relationship("Staff", foreign_keys=[master_id])
    decided_by_manager = relationship("Staff", foreign_keys=[decided_by_manager_id])

