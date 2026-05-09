"""notifications and client_email

Revision ID: a1f3f51be985
Revises: 3f6b9d7f0c21
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa


revision = "a1f3f51be985"
down_revision = "3f6b9d7f0c21"
branch_labels = None
depends_on = None


notification_kind = sa.Enum(
    "reminder_24h", "canceled", "rescheduled", name="notification_kind", create_type=False
)
notification_recipient_role = sa.Enum(
    "guest", "master", "manager", name="notification_recipient_role", create_type=False
)
notification_channel = sa.Enum(
    "email", "sms", "zalo_zns", name="notification_channel", create_type=False
)
notification_status = sa.Enum(
    "pending", "sent", "failed", "skipped", name="notification_status", create_type=False
)


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("client_email", sa.String(length=200), nullable=True),
    )

    notification_kind.create(op.get_bind(), checkfirst=True)
    notification_recipient_role.create(op.get_bind(), checkfirst=True)
    notification_channel.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", notification_kind, nullable=False),
        sa.Column("recipient_role", notification_recipient_role, nullable=False),
        sa.Column("recipient_address", sa.String(length=200), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            notification_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_notifications_appointment_id", "notifications", ["appointment_id"]
    )
    op.create_index(
        "ix_notifications_status_scheduled_at",
        "notifications",
        ["status", "scheduled_at"],
    )
    op.create_index(
        "uq_notifications_reminder_idem",
        "notifications",
        ["appointment_id", "recipient_role", "channel"],
        unique=True,
        postgresql_where=sa.text("kind = 'reminder_24h'"),
        sqlite_where=sa.text("kind = 'reminder_24h'"),
    )


def downgrade() -> None:
    op.drop_index("uq_notifications_reminder_idem", table_name="notifications")
    op.drop_index("ix_notifications_status_scheduled_at", table_name="notifications")
    op.drop_index("ix_notifications_appointment_id", table_name="notifications")
    op.drop_table("notifications")
    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_channel.drop(op.get_bind(), checkfirst=True)
    notification_recipient_role.drop(op.get_bind(), checkfirst=True)
    notification_kind.drop(op.get_bind(), checkfirst=True)
    op.drop_column("appointments", "client_email")
