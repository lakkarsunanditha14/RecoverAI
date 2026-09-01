from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.recovery_decision import (
    DecisionConfidence,
    RecoveryDecision,
)
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.recovery_decision_repository import RecoveryDecisionRepository


class RecoveryDecisionService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.recovery_decision_repository = RecoveryDecisionRepository(db)

    def create_decision(
        self,
        case_id: str,
        recommended_action: str,
        confidence: DecisionConfidence,
        rationale: str,
    ) -> RecoveryDecision:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        decision = RecoveryDecision(
            decision_id=f"decision_{uuid4().hex}",
            case_id=case.case_id,
            recommended_action=recommended_action,
            confidence=confidence,
            rationale=rationale,
            created_at=datetime.now(timezone.utc),
        )

        return self.recovery_decision_repository.save(decision)
