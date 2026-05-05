from datetime import date

from sqlalchemy import Column, Date, ForeignKey, Integer, String, UniqueConstraint
from sqlmodel import Field, SQLModel



class BranchNonWorkingDay(SQLModel, table=True):
    __tablename__ = "branch_non_working_days"
    __table_args__ = (UniqueConstraint("branch_id", "day", name="uq_branch_non_working_day"),)

    id: int | None = Field(default=None, primary_key=True)
    branch_id: int = Field(sa_column=Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), index=True))
    day: date = Field(sa_column=Column(Date, nullable=False, index=True))
    reason: str | None = Field(default=None, sa_column=Column(String(300)))

