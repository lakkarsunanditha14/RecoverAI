from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    case_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("recovery_cases.case_id"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    actor: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
