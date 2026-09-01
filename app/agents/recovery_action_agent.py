from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RecoveryActionRecommendation:
    action_type: str
    rationale: str


class RecoveryActionAgent:
    """
    Recovery action agent.

    Converts a recovery decision into a bounded action recommendation.

    The agent recommends an action but does not execute external
    payment operations.
    """

    def recommend(
        self,
        recommended_action: str,
        amount_at_risk: Decimal,
    ) -> RecoveryActionRecommendation:

        if recommended_action == "manual_review":
            return RecoveryActionRecommendation(
                action_type="manual_review",
                rationale=(
                    f"Manual review is recommended for amount at risk "
                    f"{amount_at_risk:.2f}."
                ),
            )

        if recommended_action == "retry_payment":
            return RecoveryActionRecommendation(
                action_type="retry_payment",
                rationale=(
                    f"Payment retry is recommended for amount at risk "
                    f"{amount_at_risk:.2f}."
                ),
            )

        return RecoveryActionRecommendation(
            action_type="manual_review",
            rationale=(
                f"Unsupported recovery decision for amount at risk "
                f"{amount_at_risk:.2f}; manual review is recommended."
            ),
        )
