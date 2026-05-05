from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import Field, SQLModel



class MasterProcedure(SQLModel, table=True):
    __tablename__ = "master_procedures"

    master_id: int = Field(sa_column=Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True))
    procedure_id: int = Field(
        sa_column=Column(Integer, ForeignKey("procedures.id", ondelete="CASCADE"), primary_key=True)
    )

