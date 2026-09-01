from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent
from app.models.audit_event import AuditEventModel


class AuditEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, event_id: str) -> AuditEvent | None:
        model = (
            self.db.query(AuditEventModel)
            .filter(AuditEventModel.event_id == event_id)
            .first()
        )

        if model is None:
            return None

        return AuditEvent(
            event_id=model.event_id,
            case_id=model.case_id,
            event_type=model.event_type,
            actor=model.actor,
            reason=model.reason,
            occurred_at=model.occurred_at,
        )

    def save(self, event: AuditEvent) -> AuditEvent:
        model = AuditEventModel(
            event_id=event.event_id,
            case_id=event.case_id,
            event_type=event.event_type,
            actor=event.actor,
            reason=event.reason,
            occurred_at=event.occurred_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return AuditEvent(
            event_id=model.event_id,
            case_id=model.case_id,
            event_type=model.event_type,
            actor=model.actor,
            reason=model.reason,
            occurred_at=model.occurred_at,
        )
