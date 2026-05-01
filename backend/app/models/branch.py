from datetime import datetime, time

from sqlalchemy import DateTime, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(50))
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="UTC")
    open_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(9, 0))
    close_time: Mapped[time] = mapped_column(Time, nullable=False, default=time(20, 0))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
