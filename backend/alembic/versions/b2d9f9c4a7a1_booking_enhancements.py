"""booking enhancements

Revision ID: b2d9f9c4a7a1
Revises: 8d849521862b
Create Date: 2026-04-30 23:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d9f9c4a7a1"
down_revision: Union[str, Sequence[str], None] = "8d849521862b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("procedures", sa.Column("description", sa.String(length=1000), nullable=True))
    op.add_column("procedures", sa.Column("category", sa.String(length=100), nullable=True))

    op.create_table(
        "branch_non_working_days",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=True),
        sa.UniqueConstraint("branch_id", "day", name="uq_branch_non_working_day"),
    )
    op.create_index("ix_branch_non_working_days_branch_id", "branch_non_working_days", ["branch_id"], unique=False)
    op.create_index("ix_branch_non_working_days_day", "branch_non_working_days", ["day"], unique=False)

    op.create_table(
        "appointment_procedures",
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("procedure_id", sa.Integer(), sa.ForeignKey("procedures.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("name_snapshot", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("duration_minutes_snapshot", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_snapshot", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # Backfill existing single-procedure appointments into the new join table.
    op.execute(
        """
        INSERT INTO appointment_procedures (
            appointment_id, procedure_id, sort_order, name_snapshot,
            duration_minutes_snapshot, price_snapshot
        )
        SELECT
            a.id, p.id, 0, p.name, p.duration_minutes, a.price
        FROM appointments a
        JOIN procedures p ON p.id = a.procedure_id
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("appointment_procedures")
    op.drop_index("ix_branch_non_working_days_day", table_name="branch_non_working_days")
    op.drop_index("ix_branch_non_working_days_branch_id", table_name="branch_non_working_days")
    op.drop_table("branch_non_working_days")
    op.drop_column("procedures", "category")
    op.drop_column("procedures", "description")

