"""customer crm foundation

Revision ID: d4a7f92c6e11
Revises: c3e8f02d1b74
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa


revision = "d4a7f92c6e11"
down_revision = "c3e8f02d1b74"
branch_labels = None
depends_on = None


def _phone_expr(dialect: str) -> str:
    if dialect == "postgresql":
        digits = "regexp_replace(coalesce(client_phone, ''), '\\D', '', 'g')"
        return f"CASE WHEN {digits} <> '' THEN {digits} ELSE lower(trim(coalesce(client_phone, ''))) END"
    compact = "replace(replace(replace(replace(coalesce(client_phone, ''), ' ', ''), '-', ''), '(', ''), ')', '')"
    return f"CASE WHEN {compact} <> '' THEN {compact} ELSE lower(trim(coalesce(client_phone, ''))) END"


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("phone_normalized", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("phone_normalized", name="uq_customers_phone_normalized"),
    )
    op.create_index("ix_customers_phone_normalized", "customers", ["phone_normalized"])
    op.create_index("ix_customers_email", "customers", ["email"])

    op.add_column("appointments", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_appointments_customer_id_customers",
        "appointments",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_appointments_customer_id", "appointments", ["customer_id"])

    dialect = op.get_bind().dialect.name
    phone_expr = _phone_expr(dialect)
    if dialect == "postgresql":
        op.execute(
            f"""
            INSERT INTO customers (full_name, phone, phone_normalized, email, created_at, updated_at)
            SELECT DISTINCT ON ({phone_expr})
                coalesce(nullif(trim(client_name), ''), trim(client_phone), 'Customer') AS full_name,
                coalesce(nullif(trim(client_phone), ''), 'unknown') AS phone,
                {phone_expr} AS phone_normalized,
                lower(nullif(trim(client_email), '')) AS email,
                now() AS created_at,
                now() AS updated_at
            FROM appointments
            WHERE {phone_expr} <> ''
            ORDER BY {phone_expr}, created_at
            """
        )
    else:
        op.execute(
            f"""
            INSERT OR IGNORE INTO customers (full_name, phone, phone_normalized, email, created_at, updated_at)
            SELECT
                coalesce(nullif(trim(client_name), ''), trim(client_phone), 'Customer') AS full_name,
                coalesce(nullif(trim(client_phone), ''), 'unknown') AS phone,
                {phone_expr} AS phone_normalized,
                lower(nullif(trim(client_email), '')) AS email,
                CURRENT_TIMESTAMP AS created_at,
                CURRENT_TIMESTAMP AS updated_at
            FROM appointments
            WHERE {phone_expr} <> ''
            """
        )

    op.execute(
        f"""
        UPDATE appointments
        SET customer_id = (
            SELECT customers.id
            FROM customers
            WHERE customers.phone_normalized = {phone_expr}
            LIMIT 1
        )
        WHERE customer_id IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_customer_id", table_name="appointments")
    op.drop_constraint("fk_appointments_customer_id_customers", "appointments", type_="foreignkey")
    op.drop_column("appointments", "customer_id")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_index("ix_customers_phone_normalized", table_name="customers")
    op.drop_table("customers")
