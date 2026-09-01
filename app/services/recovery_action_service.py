from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.recovery_action_agent import RecoveryActionAgent
from app.domain.recovery_action import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.repositories.recovery_action_repository import RecoveryActionRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.recovery_decision_repository import RecoveryDecisionRepository
from app.services.recovery_decision_service import RecoveryDecisionService


class RecoveryActionService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.recovery_action_repository = RecoveryActionRepository(db)
        self.recovery_decision_repository = RecoveryDecisionRepository(db)
        self.recovery_decision_service = RecoveryDecisionService(db)
        self.agent = RecoveryActionAgent()

    def propose_action(
        self,
        case_id: str,
        action_type: RecoveryActionType | None = None,
    ) -> RecoveryAction:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        if action_type is None:
            decision = self.recovery_decision_repository.get_latest_by_case_id(
                case_id
            )

            if decision is None:
                decision = self.recovery_decision_service.create_decision(
                    case_id=case_id,
                )

            recommendation = self.agent.recommend(
                recommended_action=decision.recommended_action,
                amount_at_risk=case.amount_at_risk,
            )

            action_type = RecoveryActionType(recommendation.action_type)

        action = RecoveryAction(
            action_id=f"action_{uuid4().hex}",
            case_id=case.case_id,
            action_type=action_type,
            status=RecoveryActionStatus.PROPOSED,
            proposed_at=datetime.now(timezone.utc),
        )

        return self.recovery_action_repository.save(action)
