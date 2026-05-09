"""fix reminder idempotency index to pending status only

Revision ID: c3e8f02d1b74
Revises: a1f3f51be985
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa


revision = "c3e8f02d1b74"
down_revision = "a1f3f51be985"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("uq_notifications_reminder_idem", table_name="notifications")
    op.create_index(
        "uq_notifications_reminder_idem",
        "notifications",
        ["appointment_id", "recipient_role", "channel"],
        unique=True,
        postgresql_where=sa.text("kind = 'reminder_24h' AND status = 'pending'"),
        sqlite_where=sa.text("kind = 'reminder_24h' AND status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("uq_notifications_reminder_idem", table_name="notifications")
    op.create_index(
        "uq_notifications_reminder_idem",
        "notifications",
        ["appointment_id", "recipient_role", "channel"],
        unique=True,
        postgresql_where=sa.text("kind = 'reminder_24h'"),
        sqlite_where=sa.text("kind = 'reminder_24h'"),
    )
