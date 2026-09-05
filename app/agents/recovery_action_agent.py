from dataclasses import dataclass
from decimal import Decimal
from app.domain.recovery_action import RecoveryActionType


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

        # Any action the domain defines is honoured. The previous version
        # recognised only manual_review and retry_payment, so every other
        # strategy the policy produced silently became manual_review.
        try:
            action_type = RecoveryActionType(recommended_action)
        except ValueError:
            return RecoveryActionRecommendation(
                action_type="manual_review",
                rationale=(
                    f"Unsupported recovery decision for amount at risk "
                    f"{amount_at_risk:.2f}; manual review is recommended."
                ),
            )

        rationales = {
            RecoveryActionType.RETRY_PAYMENT: "Payment retry is recommended",
            RecoveryActionType.SEND_REMINDER: "A customer reminder is recommended",
            RecoveryActionType.UPDATE_PAYMENT_METHOD: (
                "Updating the payment method is recommended"
            ),
            RecoveryActionType.OFFER_ALTERNATIVE_METHOD: (
                "Offering an alternative method is recommended"
            ),
            RecoveryActionType.ESCALATE: "Escalation is recommended",
            RecoveryActionType.MANUAL_REVIEW: "Manual review is recommended",
        }

        return RecoveryActionRecommendation(
            action_type=str(action_type),
            rationale=(
                f"{rationales[action_type]} for amount at risk "
                f"{amount_at_risk:.2f}."
            ),
        )
