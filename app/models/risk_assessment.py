from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    case_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    amount_at_risk: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    recoverability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    assessed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
