from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.diagnosis import Diagnosis, FailureCategory

# Guardrails. These are the authorisation boundary: the agent recommends,
# this policy decides, and nothing downstream may override it.
MAX_RETRIES = 3
RECOVERY_WINDOW_DAYS = 7
HIGH_RISK_THRESHOLD = 70
HIGH_VALUE_THRESHOLD = Decimal("50000")


@dataclass(frozen=True)
class RecoveryDecisionRecommendation:
    recommended_action: str
    confidence: str
    rationale: str


@dataclass(frozen=True)
class PolicyDecision:
    """The result of the authorisation check, not a suggestion."""

    action: str
    authorized: bool
    escalate: bool
    stop: bool
    reason: str
    requires_review: bool = False
    factors: list[str] = field(default_factory=list)


class RecoveryDecisionPolicy:
    """
    Deterministic recovery policy.

    `recommend` produces an advisory recommendation. `authorize` is the
    binding decision: it is evaluated after the agent has spoken and its
    result cannot be bypassed by the recommendation layer.
    """

    def recommend(
        self,
        risk_score: float,
        recoverability_score: float,
        amount_at_risk: float,
        diagnosis: Diagnosis | None = None,
    ) -> RecoveryDecisionRecommendation:
        # Strategy selection by recoverability, so cases do not all
        # collapse onto retry_payment.
        if risk_score >= HIGH_RISK_THRESHOLD or recoverability_score < 40:
            return RecoveryDecisionRecommendation(
                recommended_action="escalate",
                confidence="high",
                rationale=(
                    f"Risk {risk_score:.0f} with recoverability "
                    f"{recoverability_score:.0f} on {amount_at_risk:.2f}; "
                    f"human review is recommended."
                ),
            )

        # The diagnosis answers a question recoverability cannot: what
        # actually went wrong. Charging an expired card a second time
        # fails for the same reason it failed the first time, however
        # recoverable the case looks on score alone.
        if diagnosis is not None:
            matched = self._strategy_for(diagnosis, amount_at_risk)

            if matched is not None:
                return matched

        if recoverability_score >= 80:
            return RecoveryDecisionRecommendation(
                recommended_action="retry_payment",
                confidence="high",
                rationale=(
                    f"Recoverability {recoverability_score:.0f} on "
                    f"{amount_at_risk:.2f}; an immediate retry is likely "
                    f"to succeed."
                ),
            )

        if recoverability_score >= 60:
            return RecoveryDecisionRecommendation(
                recommended_action="send_reminder",
                confidence="medium",
                rationale=(
                    f"Recoverability {recoverability_score:.0f} on "
                    f"{amount_at_risk:.2f}; prompting the customer is "
                    f"more likely to work than an immediate retry."
                ),
            )

        return RecoveryDecisionRecommendation(
            recommended_action="update_payment_method",
            confidence="medium",
            rationale=(
                f"Recoverability {recoverability_score:.0f} on "
                f"{amount_at_risk:.2f}; the payment method itself is the "
                f"likely obstacle."
            ),
        )

    @staticmethod
    def _strategy_for(
        diagnosis: Diagnosis,
        amount_at_risk: float,
    ) -> RecoveryDecisionRecommendation | None:
        """
        Map a diagnosed cause onto the action that addresses it.

        Returns None when the diagnosis carries no strategy signal, so
        selection falls back to the recoverability bands.
        """
        by_category = {
            FailureCategory.CARD_EXPIRED: "update_payment_method",
            FailureCategory.PAYMENT_METHOD_INVALID: "update_payment_method",
            FailureCategory.INSUFFICIENT_FUNDS: "send_reminder",
            FailureCategory.BANK_TIMEOUT: "retry_payment",
            FailureCategory.PERSISTENT_DECLINE: "offer_alternative_method",
            FailureCategory.GATEWAY_UNCERTAIN: "escalate",
        }

        action = by_category.get(diagnosis.category)

        if action is None:
            return None

        # A cause that cannot clear on a retry must not be retried, even
        # where the score would otherwise allow it.
        if action == "retry_payment" and not diagnosis.retry_viable:
            action = "offer_alternative_method"

        return RecoveryDecisionRecommendation(
            recommended_action=action,
            confidence=diagnosis.confidence,
            rationale=(
                f"Diagnosed as {diagnosis.category} on "
                f"{amount_at_risk:.2f}: {diagnosis.rationale}"
            ),
        )

    def authorize(
        self,
        recommended_action: str,
        risk_score: float,
        recoverability_score: float,
        amount_at_risk: Decimal,
        retry_count: int,
        payment_already_recovered: bool,
        diagnosis: Diagnosis | None = None,
    ) -> PolicyDecision:
        factors = [
            f"risk_score={risk_score:.0f}",
            f"recoverability={recoverability_score:.0f}",
            f"retry_count={retry_count}/{MAX_RETRIES}",
            f"amount_at_risk={amount_at_risk:.2f}",
            f"recommended={recommended_action}",
        ]

        if diagnosis is not None:
            factors.append(f"diagnosis={diagnosis.category}")

        if payment_already_recovered:
            return PolicyDecision(
                action="none",
                authorized=False,
                escalate=False,
                stop=True,
                reason="payment_already_recovered",
                factors=factors,
            )

        if retry_count >= MAX_RETRIES:
            return PolicyDecision(
                action="escalate",
                authorized=False,
                escalate=True,
                stop=True,
                reason="maximum_retry_limit_reached",
                factors=factors,
            )

        if risk_score >= HIGH_RISK_THRESHOLD:
            return PolicyDecision(
                action="escalate",
                authorized=False,
                escalate=True,
                stop=True,
                reason="high_risk_case",
                factors=factors,
            )

        if Decimal(amount_at_risk) >= HIGH_VALUE_THRESHOLD:
            return PolicyDecision(
                action="escalate",
                authorized=False,
                escalate=True,
                stop=True,
                reason="high_value_requires_policy_review",
                requires_review=True,
                factors=factors,
            )

        # Where the cause is known, it decides the strategy. The policy
        # derives that strategy itself rather than trusting the action
        # the agent asked for, so this stays the authorisation boundary
        # while still acting on the diagnosis.
        if diagnosis is not None:
            directed = self._strategy_for(diagnosis, float(amount_at_risk))

            if directed is not None:
                action = directed.recommended_action
                escalating = action == "escalate"

                return PolicyDecision(
                    action=action,
                    authorized=not escalating,
                    escalate=escalating,
                    stop=escalating,
                    reason=f"diagnosis_{diagnosis.category}",
                    factors=factors + [
                        f"retry_viable={diagnosis.retry_viable}"
                    ],
                )

        if recoverability_score >= 80 and retry_count == 0:
            return PolicyDecision(
                action="retry_payment",
                authorized=True,
                escalate=False,
                stop=False,
                reason="high_recoverability_first_attempt",
                factors=factors,
            )

        if recoverability_score >= 60:
            return PolicyDecision(
                action="send_reminder",
                authorized=True,
                escalate=False,
                stop=False,
                reason="moderate_recoverability_reminder",
                factors=factors,
            )

        if recoverability_score >= 40:
            return PolicyDecision(
                action="update_payment_method",
                authorized=True,
                escalate=False,
                stop=False,
                reason="low_recoverability_payment_method",
                factors=factors,
            )

        return PolicyDecision(
            action="escalate",
            authorized=False,
            escalate=True,
            stop=True,
            reason="recoverability_below_automation_threshold",
            factors=factors,
        )
