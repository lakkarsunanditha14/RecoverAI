from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.agents.recovery_decision_agent import RecoveryDecisionAgent
from app.domain.recovery_decision import (
    DecisionConfidence,
    RecoveryDecision,
)
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.recovery_decision_repository import RecoveryDecisionRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository


class RecoveryDecisionService:
    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.recovery_decision_repository = RecoveryDecisionRepository(db)
        self.risk_assessment_repository = RiskAssessmentRepository(db)
        self.agent = RecoveryDecisionAgent()

    def create_decision(
        self,
        case_id: str,
        recommended_action: str | None = None,
        confidence: DecisionConfidence | None = None,
        rationale: str | None = None,
    ) -> RecoveryDecision:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        assessment = self.risk_assessment_repository.get_latest_by_case_id(
            case_id
        )

        if assessment is not None:
            agent_result = self.agent.decide(
                case_id=case.case_id,
                amount_at_risk=assessment.amount_at_risk,
                risk_score=assessment.risk_score,
                recoverability_score=assessment.recoverability_score,
            )

            recommended_action = agent_result.recommended_action
            confidence = DecisionConfidence(agent_result.confidence)
            rationale = agent_result.rationale

        if recommended_action is None:
            recommended_action = "retry_payment"

        if confidence is None:
            confidence = DecisionConfidence.MEDIUM

        if rationale is None:
            rationale = (
                f"Recovery decision created for amount at risk "
                f"{case.amount_at_risk:.2f}."
            )

        decision = RecoveryDecision(
            decision_id=f"decision_{uuid4().hex}",
            case_id=case.case_id,
            recommended_action=recommended_action,
            confidence=confidence,
            rationale=rationale,
            created_at=datetime.now(timezone.utc),
        )

        return self.recovery_decision_repository.save(decision)
