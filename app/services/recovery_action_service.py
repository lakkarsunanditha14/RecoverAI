from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.recovery_action import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.repositories.recovery_action_repository import RecoveryActionRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository


class RecoveryActionService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.recovery_action_repository = RecoveryActionRepository(db)

    def propose_action(
        self,
        case_id: str,
        action_type: RecoveryActionType,
    ) -> RecoveryAction:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        action = RecoveryAction(
            action_id=f"action_{uuid4().hex}",
            case_id=case.case_id,
            action_type=action_type,
            status=RecoveryActionStatus.PROPOSED,
            proposed_at=datetime.now(timezone.utc),
        )

        return self.recovery_action_repository.save(action)
