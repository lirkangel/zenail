"""branch timezones and booking references

Revision ID: 3f6b9d7f0c21
Revises: b2d9f9c4a7a1
Create Date: 2026-05-01 14:45:00.000000

"""

from typing import Sequence, Union
import secrets

from alembic import op
import sqlalchemy as sa


revision: str = "3f6b9d7f0c21"
down_revision: Union[str, Sequence[str], None] = "b2d9f9c4a7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_reference() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


def upgrade() -> None:
    op.add_column("branches", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.execute("UPDATE branches SET timezone = 'UTC' WHERE timezone IS NULL")
    op.alter_column("branches", "timezone", nullable=False)

    op.add_column("appointments", sa.Column("booking_reference", sa.String(length=32), nullable=True))

    bind = op.get_bind()
    appointment_ids = [row[0] for row in bind.execute(sa.text("SELECT id FROM appointments ORDER BY id")).fetchall()]
    for appointment_id in appointment_ids:
        reference = _generate_reference()
        while bind.execute(
            sa.text("SELECT 1 FROM appointments WHERE booking_reference = :reference"),
            {"reference": reference},
        ).fetchone():
            reference = _generate_reference()
        bind.execute(
            sa.text("UPDATE appointments SET booking_reference = :reference WHERE id = :appointment_id"),
            {"reference": reference, "appointment_id": appointment_id},
        )

    op.alter_column("appointments", "booking_reference", nullable=False)
    op.create_index("ix_appointments_booking_reference", "appointments", ["booking_reference"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_appointments_booking_reference", table_name="appointments")
    op.drop_column("appointments", "booking_reference")
    op.drop_column("branches", "timezone")
