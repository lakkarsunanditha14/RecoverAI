from dataclasses import dataclass
from decimal import Decimal

from app.policies.recovery_decision_policy import (
    RecoveryDecisionPolicy,
    RecoveryDecisionRecommendation,
)


@dataclass(frozen=True)
class RecoveryDecisionAgentResult:
    case_id: str
    amount_at_risk: Decimal
    risk_score: float
    recoverability_score: float
    recommended_action: str
    confidence: str
    rationale: str


class RecoveryDecisionAgent:
    """
    Recovery decision agent.

    The agent consumes an existing risk assessment and
    converts it into a bounded recovery recommendation.

    The agent does not execute recovery actions.
    """

    def __init__(self):
        self.policy = RecoveryDecisionPolicy()

    def decide(
        self,
        case_id: str,
        amount_at_risk: Decimal,
        risk_score: float,
        recoverability_score: float,
    ) -> RecoveryDecisionAgentResult:
        recommendation: RecoveryDecisionRecommendation = self.policy.recommend(
            risk_score=risk_score,
            recoverability_score=recoverability_score,
            amount_at_risk=float(amount_at_risk),
        )

        return RecoveryDecisionAgentResult(
            case_id=case_id,
            amount_at_risk=amount_at_risk,
            risk_score=risk_score,
            recoverability_score=recoverability_score,
            recommended_action=recommendation.recommended_action,
            confidence=recommendation.confidence,
            rationale=recommendation.rationale,
        )
