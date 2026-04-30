from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MasterProcedure(Base):
    __tablename__ = "master_procedures"

    master_id: Mapped[int] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"),
        primary_key=True,
    )
    procedure_id: Mapped[int] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"),
        primary_key=True,
    )

