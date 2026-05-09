import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlmodel import Field, SQLModel


class NotificationKind(str, enum.Enum):
    reminder_24h = "reminder_24h"
    canceled = "canceled"
    rescheduled = "rescheduled"


class NotificationRecipientRole(str, enum.Enum):
    guest = "guest"
    master = "master"
    manager = "manager"


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    zalo_zns = "zalo_zns"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)

    appointment_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    kind: NotificationKind = Field(
        sa_column=Column(Enum(NotificationKind, name="notification_kind"), nullable=False)
    )
    recipient_role: NotificationRecipientRole = Field(
        sa_column=Column(
            Enum(NotificationRecipientRole, name="notification_recipient_role"),
            nullable=False,
        )
    )
    recipient_address: str = Field(sa_column=Column(String(200), nullable=False))
    channel: NotificationChannel = Field(
        sa_column=Column(Enum(NotificationChannel, name="notification_channel"), nullable=False)
    )
    template_key: str = Field(sa_column=Column(String(64), nullable=False))
    payload_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: NotificationStatus = Field(
        default=NotificationStatus.pending,
        sa_column=Column(
            Enum(NotificationStatus, name="notification_status"),
            nullable=False,
        ),
    )

    scheduled_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    sent_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    attempt_count: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    last_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow
        ),
    )
