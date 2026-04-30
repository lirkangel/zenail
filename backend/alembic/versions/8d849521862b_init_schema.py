"""init schema

Revision ID: 8d849521862b
Revises: 
Create Date: 2026-04-30 22:17:51.008855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d849521862b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    staff_role = sa.Enum("master", "manager", "admin", name="staff_role")
    appointment_status = sa.Enum("scheduled", "completed", "canceled", name="appointment_status")
    reschedule_request_status = sa.Enum(
        "pending", "approved", "rejected", name="reschedule_request_status"
    )

    staff_role.create(op.get_bind(), checkfirst=True)
    appointment_status.create(op.get_bind(), checkfirst=True)
    reschedule_request_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "branches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("open_time", sa.Time(), nullable=False),
        sa.Column("close_time", sa.Time(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("role", staff_role, nullable=False),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_staff_email", "staff", ["email"], unique=True)

    op.create_table(
        "procedures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "master_procedures",
        sa.Column("master_id", sa.Integer(), sa.ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("procedure_id", sa.Integer(), sa.ForeignKey("procedures.id", ondelete="CASCADE"), primary_key=True),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("master_id", sa.Integer(), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("procedure_id", sa.Integer(), sa.ForeignKey("procedures.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("client_name", sa.String(length=200), nullable=False),
        sa.Column("client_phone", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", appointment_status, nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_branch_id_start_time", "appointments", ["branch_id", "start_time"], unique=False)
    op.create_index("ix_appointments_master_id_start_time", "appointments", ["master_id", "start_time"], unique=False)

    op.create_table(
        "reschedule_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("master_id", sa.Integer(), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("proposed_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("status", reschedule_request_status, nullable=False, server_default="pending"),
        sa.Column("decided_by_manager_id", sa.Integer(), sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reschedule_requests_appointment_id", "reschedule_requests", ["appointment_id"], unique=False)
    op.create_index("ix_reschedule_requests_master_id", "reschedule_requests", ["master_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_reschedule_requests_master_id", table_name="reschedule_requests")
    op.drop_index("ix_reschedule_requests_appointment_id", table_name="reschedule_requests")
    op.drop_table("reschedule_requests")

    op.drop_index("ix_appointments_master_id_start_time", table_name="appointments")
    op.drop_index("ix_appointments_branch_id_start_time", table_name="appointments")
    op.drop_table("appointments")

    op.drop_table("master_procedures")
    op.drop_table("procedures")

    op.drop_index("ix_staff_email", table_name="staff")
    op.drop_table("staff")

    op.drop_table("branches")

    sa.Enum(name="reschedule_request_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="appointment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="staff_role").drop(op.get_bind(), checkfirst=True)
