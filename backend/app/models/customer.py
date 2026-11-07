import enum
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DefinitionScope(str, enum.Enum):
    global_ = "global"
    branch = "branch"


class PreferenceValueType(str, enum.Enum):
    text = "text"
    boolean = "boolean"
    single_select = "single_select"


class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: int | None = Field(default=None, primary_key=True)
    full_name: str = Field(sa_column=Column(String(200), nullable=False))
    phone: str = Field(sa_column=Column(String(50), nullable=False))
    phone_normalized: str = Field(sa_column=Column(String(50), nullable=False, unique=True, index=True))
    email: str | None = Field(default=None, sa_column=Column(String(200), nullable=True, index=True))
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    merged_into_customer_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("customers.id"), nullable=True, index=True),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class CustomerTagDefinition(SQLModel, table=True):
    __tablename__ = "customer_tag_definitions"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    slug: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    scope: DefinitionScope = Field(
        sa_column=Column(Enum(DefinitionScope, name="definition_scope"), nullable=False)
    )
    branch_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    created_by_staff_id: int = Field(
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class CustomerPreferenceDefinition(SQLModel, table=True):
    __tablename__ = "customer_preference_definitions"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    slug: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    scope: DefinitionScope = Field(
        sa_column=Column(Enum(DefinitionScope, name="definition_scope"), nullable=False)
    )
    branch_id: int | None = Field(
        default=None,
        sa_column=Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=True),
    )
    value_type: PreferenceValueType = Field(
        sa_column=Column(Enum(PreferenceValueType, name="preference_value_type"), nullable=False)
    )
    options_json: list[str] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    is_active: bool = Field(default=True, sa_column=Column(Boolean, nullable=False))
    created_by_staff_id: int = Field(
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class CustomerTag(SQLModel, table=True):
    __tablename__ = "customer_tags"

    customer_id: int = Field(
        sa_column=Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    )
    tag_definition_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("customer_tag_definitions.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    assigned_by_staff_id: int = Field(
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class CustomerPreferenceValue(SQLModel, table=True):
    __tablename__ = "customer_preference_values"

    customer_id: int = Field(
        sa_column=Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), primary_key=True)
    )
    preference_definition_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("customer_preference_definitions.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    value_text: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    value_bool: bool | None = Field(default=None, sa_column=Column(Boolean, nullable=True))
    value_option: str | None = Field(default=None, sa_column=Column(String(120), nullable=True))
    updated_by_staff_id: int = Field(
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, onupdate=utc_now),
    )


class CustomerMergeLog(SQLModel, table=True):
    __tablename__ = "customer_merge_logs"

    id: int | None = Field(default=None, primary_key=True)
    source_customer_id: int = Field(
        sa_column=Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    )
    target_customer_id: int = Field(
        sa_column=Column(Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    )
    performed_by_staff_id: int = Field(
        sa_column=Column(Integer, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    )
    summary_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
