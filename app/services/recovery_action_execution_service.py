from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEvent, AuditEventType
from app.domain.recovery_action import RecoveryAction
from app.repositories.audit_event_repository import AuditEventRepository
from app.repositories.recovery_action_repository import RecoveryActionRepository


class RecoveryActionExecutionService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_action_repository = RecoveryActionRepository(db)
        self.audit_event_repository = AuditEventRepository(db)

    def approve_action(self, action_id: str) -> RecoveryAction:
        action = self._get_action(action_id)

        approved_action = action.approve()
        saved_action = self.recovery_action_repository.update(
            approved_action
        )

        self._record_execution_event(
            action=saved_action,
            reason="Recovery action approved.",
        )

        return saved_action

    def start_execution(self, action_id: str) -> RecoveryAction:
        action = self._get_action(action_id)

        executing_action = action.start_execution()
        saved_action = self.recovery_action_repository.update(
            executing_action
        )

        self._record_execution_event(
            action=saved_action,
            reason="Recovery action execution started.",
        )

        return saved_action

    def complete_action(self, action_id: str) -> RecoveryAction:
        action = self._get_action(action_id)

        completed_action = action.complete()
        saved_action = self.recovery_action_repository.update(
            completed_action
        )

        self._record_execution_event(
            action=saved_action,
            reason="Recovery action completed.",
        )

        return saved_action

    def fail_action(self, action_id: str) -> RecoveryAction:
        action = self._get_action(action_id)

        failed_action = action.fail()
        saved_action = self.recovery_action_repository.update(
            failed_action
        )

        self._record_execution_event(
            action=saved_action,
            reason="Recovery action failed.",
        )

        return saved_action

    def _get_action(self, action_id: str) -> RecoveryAction:
        action = self.recovery_action_repository.get_by_id(action_id)

        if action is None:
            raise ValueError(
                f"Recovery action not found: {action_id}"
            )

        return action

    def _record_execution_event(
        self,
        action: RecoveryAction,
        reason: str,
    ) -> None:
        event = AuditEvent(
            event_id=f"event_{uuid4().hex}",
            case_id=action.case_id,
            event_type=AuditEventType.ACTION_EXECUTED,
            actor="recovery_action_service",
            reason=reason,
            occurred_at=datetime.now(timezone.utc),
        )

        self.audit_event_repository.save(event)
