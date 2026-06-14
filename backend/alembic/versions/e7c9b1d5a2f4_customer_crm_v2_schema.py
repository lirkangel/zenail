"""customer crm v2 schema

Revision ID: e7c9b1d5a2f4
Revises: d4a7f92c6e11
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa


revision = "e7c9b1d5a2f4"
down_revision = "d4a7f92c6e11"
branch_labels = None
depends_on = None


definition_scope = sa.Enum("global", "branch", name="definition_scope")
preference_value_type = sa.Enum("text", "boolean", "single_select", name="preference_value_type")


def _scope_equals(value: str) -> sa.TextClause:
    return sa.text(f"scope = '{value}'")


def upgrade() -> None:
    op.add_column("customers", sa.Column("merged_into_customer_id", sa.Integer(), nullable=True))
    op.add_column(
        "customers",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_foreign_key(
        "fk_customers_merged_into_customer_id",
        "customers",
        "customers",
        ["merged_into_customer_id"],
        ["id"],
    )
    op.create_index(
        "ix_customers_merged_into_customer_id",
        "customers",
        ["merged_into_customer_id"],
        unique=False,
    )
    op.alter_column("customers", "is_active", server_default=None)

    op.create_table(
        "customer_tag_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("scope", definition_scope, nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_staff_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_staff_id"], ["staff.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_customer_tag_definitions_name", "customer_tag_definitions", ["name"], unique=False)
    op.create_index("ix_customer_tag_definitions_slug", "customer_tag_definitions", ["slug"], unique=False)
    op.create_index(
        "uq_customer_tag_definitions_global_slug",
        "customer_tag_definitions",
        ["slug"],
        unique=True,
        postgresql_where=_scope_equals("global"),
        sqlite_where=_scope_equals("global"),
    )
    op.create_index(
        "uq_customer_tag_definitions_branch_slug",
        "customer_tag_definitions",
        ["branch_id", "slug"],
        unique=True,
        postgresql_where=_scope_equals("branch"),
        sqlite_where=_scope_equals("branch"),
    )
    op.alter_column("customer_tag_definitions", "is_active", server_default=None)

    op.create_table(
        "customer_preference_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("scope", definition_scope, nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.Column("value_type", preference_value_type, nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by_staff_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_staff_id"], ["staff.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_customer_preference_definitions_name",
        "customer_preference_definitions",
        ["name"],
        unique=False,
    )
    op.create_index(
        "ix_customer_preference_definitions_slug",
        "customer_preference_definitions",
        ["slug"],
        unique=False,
    )
    op.create_index(
        "uq_customer_preference_definitions_global_slug",
        "customer_preference_definitions",
        ["slug"],
        unique=True,
        postgresql_where=_scope_equals("global"),
        sqlite_where=_scope_equals("global"),
    )
    op.create_index(
        "uq_customer_preference_definitions_branch_slug",
        "customer_preference_definitions",
        ["branch_id", "slug"],
        unique=True,
        postgresql_where=_scope_equals("branch"),
        sqlite_where=_scope_equals("branch"),
    )
    op.alter_column("customer_preference_definitions", "is_active", server_default=None)

    op.create_table(
        "customer_tags",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("tag_definition_id", sa.Integer(), nullable=False),
        sa.Column("assigned_by_staff_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_staff_id"], ["staff.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["tag_definition_id"],
            ["customer_tag_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("customer_id", "tag_definition_id"),
    )

    op.create_table(
        "customer_preference_values",
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("preference_definition_id", sa.Integer(), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("value_option", sa.String(length=120), nullable=True),
        sa.Column("updated_by_staff_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["preference_definition_id"],
            ["customer_preference_definitions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["updated_by_staff_id"], ["staff.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("customer_id", "preference_definition_id"),
    )

    op.create_table(
        "customer_merge_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_customer_id", sa.Integer(), nullable=False),
        sa.Column("target_customer_id", sa.Integer(), nullable=False),
        sa.Column("performed_by_staff_id", sa.Integer(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["performed_by_staff_id"], ["staff.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_customer_id"], ["customers.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_customer_merge_logs_source_customer_id",
        "customer_merge_logs",
        ["source_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_customer_merge_logs_target_customer_id",
        "customer_merge_logs",
        ["target_customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customer_merge_logs_target_customer_id", table_name="customer_merge_logs")
    op.drop_index("ix_customer_merge_logs_source_customer_id", table_name="customer_merge_logs")
    op.drop_table("customer_merge_logs")
    op.drop_table("customer_preference_values")
    op.drop_table("customer_tags")
    op.drop_index(
        "uq_customer_preference_definitions_branch_slug",
        table_name="customer_preference_definitions",
    )
    op.drop_index(
        "uq_customer_preference_definitions_global_slug",
        table_name="customer_preference_definitions",
    )
    op.drop_index("ix_customer_preference_definitions_slug", table_name="customer_preference_definitions")
    op.drop_index("ix_customer_preference_definitions_name", table_name="customer_preference_definitions")
    op.drop_table("customer_preference_definitions")
    op.drop_index("uq_customer_tag_definitions_branch_slug", table_name="customer_tag_definitions")
    op.drop_index("uq_customer_tag_definitions_global_slug", table_name="customer_tag_definitions")
    op.drop_index("ix_customer_tag_definitions_slug", table_name="customer_tag_definitions")
    op.drop_index("ix_customer_tag_definitions_name", table_name="customer_tag_definitions")
    op.drop_table("customer_tag_definitions")
    op.drop_index("ix_customers_merged_into_customer_id", table_name="customers")
    op.drop_constraint("fk_customers_merged_into_customer_id", "customers", type_="foreignkey")
    op.drop_column("customers", "is_active")
    op.drop_column("customers", "merged_into_customer_id")
