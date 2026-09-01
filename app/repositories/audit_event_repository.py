from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent, AuditEventType
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

        return self._to_domain(model)

    def get_by_case_id(self, case_id: str) -> list[AuditEvent]:
        models = (
            self.db.query(AuditEventModel)
            .filter(AuditEventModel.case_id == case_id)
            .order_by(AuditEventModel.occurred_at.asc())
            .all()
        )

        return [self._to_domain(model) for model in models]

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

        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            event_id=model.event_id,
            case_id=model.case_id,
            event_type=AuditEventType(model.event_type),
            actor=model.actor,
            reason=model.reason,
            occurred_at=model.occurred_at,
        )
