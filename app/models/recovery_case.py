from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecoveryCaseModel(Base):
    __tablename__ = "recovery_cases"

    case_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    payment_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("payments.payment_id"),
        nullable=False,
    )

    customer_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    amount_at_risk: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
