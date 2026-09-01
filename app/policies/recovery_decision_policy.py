from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryDecisionRecommendation:
    recommended_action: str
    confidence: str
    rationale: str


class RecoveryDecisionPolicy:
    """
    Deterministic recovery policy.

    The policy converts risk and recoverability signals into a
    bounded recovery recommendation.

    It does not execute the action.
    """

    def recommend(
        self,
        risk_score: float,
        recoverability_score: float,
        amount_at_risk: float,
    ) -> RecoveryDecisionRecommendation:
        if risk_score >= 70 or recoverability_score <= 30:
            return RecoveryDecisionRecommendation(
                recommended_action="manual_review",
                confidence="high",
                rationale=(
                    f"High recovery risk detected for amount at risk "
                    f"{amount_at_risk:.2f}; manual review is recommended."
                ),
            )

        if risk_score >= 40 or recoverability_score <= 60:
            return RecoveryDecisionRecommendation(
                recommended_action="retry_payment",
                confidence="medium",
                rationale=(
                    f"Moderate recovery risk detected for amount at risk "
                    f"{amount_at_risk:.2f}; retrying the payment is "
                    f"recommended."
                ),
            )

        return RecoveryDecisionRecommendation(
            recommended_action="retry_payment",
            confidence="high",
            rationale=(
                f"Low recovery risk and favorable recoverability detected "
                f"for amount at risk {amount_at_risk:.2f}; retrying the "
                f"payment is recommended."
            ),
        )
