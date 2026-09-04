from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent, AuditEventType
from app.repositories.audit_event_repository import AuditEventRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository


class AuditEventService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.audit_event_repository = AuditEventRepository(db)

    def record_event(
        self,
        case_id: str,
        event_type: str,
        actor: str,
        reason: str,
    ) -> AuditEvent:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        try:
            normalized_event_type = AuditEventType(event_type)
        except ValueError:
            raise ValueError(
                f"Invalid audit event type: {event_type}"
            )

        event = AuditEvent(
            event_id=f"event_{uuid4().hex}",
            case_id=case.case_id,
            event_type=normalized_event_type,
            actor=actor,
            reason=reason,
            occurred_at=datetime.now(timezone.utc),
        )

        return self.audit_event_repository.save(event)

    def get_recent_events(self, limit: int = 10) -> list[AuditEvent]:
        return self.audit_event_repository.list_recent(limit)

    def get_case_events(self, case_id: str) -> list[AuditEvent]:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        return self.audit_event_repository.get_by_case_id(case_id)
