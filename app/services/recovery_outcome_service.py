from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.recovery_outcome import (
    RecoveryOutcome,
    RecoveryOutcomeStatus,
)
from app.domain.recovery_case import RecoveryCaseStatus
from app.repositories.recovery_action_repository import RecoveryActionRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.recovery_outcome_repository import RecoveryOutcomeRepository


class RecoveryOutcomeService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.recovery_action_repository = RecoveryActionRepository(db)
        self.recovery_outcome_repository = RecoveryOutcomeRepository(db)

    def record_outcome(
        self,
        case_id: str,
        action_id: str,
        status: RecoveryOutcomeStatus,
        amount_recovered: Decimal,
    ) -> RecoveryOutcome:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        action = self.recovery_action_repository.get_by_id(action_id)

        if action is None:
            raise ValueError(f"Recovery action not found: {action_id}")

        if action.case_id != case.case_id:
            raise ValueError(
                f"Recovery action {action_id} does not belong to case {case_id}"
            )

        outcome = RecoveryOutcome(
            outcome_id=f"outcome_{uuid4().hex}",
            case_id=case.case_id,
            action_id=action.action_id,
            status=status,
            amount_recovered=amount_recovered,
            recorded_at=datetime.now(timezone.utc),
        )

        saved_outcome = self.recovery_outcome_repository.save(outcome)

        if status == RecoveryOutcomeStatus.RECOVERED:
            self.recovery_case_repository.update_status(
                case_id=case.case_id,
                status=RecoveryCaseStatus.RECOVERED,
            )
        elif status == RecoveryOutcomeStatus.NOT_RECOVERED:
            self.recovery_case_repository.update_status(
                case_id=case.case_id,
                status=RecoveryCaseStatus.FAILED,
            )

        return saved_outcome
