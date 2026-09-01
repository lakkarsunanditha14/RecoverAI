from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecoveryOutcomeModel(Base):
    __tablename__ = "recovery_outcomes"

    outcome_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    case_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
    )

    action_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("recovery_actions.action_id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    amount_recovered: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
