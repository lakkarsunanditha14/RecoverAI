from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecoveryActionModel(Base):
    __tablename__ = "recovery_actions"

    action_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    case_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    proposed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
