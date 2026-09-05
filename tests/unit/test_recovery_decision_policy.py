from decimal import Decimal

from app.policies.recovery_decision_policy import (
    HIGH_RISK_THRESHOLD,
    HIGH_VALUE_THRESHOLD,
    MAX_RETRIES,
    RecoveryDecisionPolicy,
)


def make_policy():
    return RecoveryDecisionPolicy()


def authorize(**overrides):
    request = {
        "recommended_action": "retry_payment",
        "risk_score": 20.0,
        "recoverability_score": 90.0,
        "amount_at_risk": Decimal("4999.00"),
        "retry_count": 0,
        "payment_already_recovered": False,
    }
    request.update(overrides)

    return make_policy().authorize(**request)


# --- recommendation: one strategy per band -----------------------------


def test_high_recoverability_recommends_retry():
    recommendation = make_policy().recommend(15.0, 90.0, 4999.00)

    assert recommendation.recommended_action == "retry_payment"
    assert recommendation.confidence == "high"
    assert "4999.00" in recommendation.rationale


def test_moderate_recoverability_recommends_reminder():
    recommendation = make_policy().recommend(45.0, 68.0, 4999.00)

    assert recommendation.recommended_action == "send_reminder"
    assert recommendation.confidence == "medium"


def test_low_recoverability_recommends_payment_method_update():
    recommendation = make_policy().recommend(55.0, 45.0, 4999.00)

    assert recommendation.recommended_action == "update_payment_method"


def test_high_risk_recommends_escalation():
    recommendation = make_policy().recommend(82.0, 30.0, 4999.00)

    assert recommendation.recommended_action == "escalate"
    assert "human review" in recommendation.rationale


def test_strategies_are_not_all_the_same():
    # The whole point of the strategy table: different cases must
    # produce different actions, not retry_payment every time.
    policy = make_policy()
    actions = {
        policy.recommend(risk, recoverability, 4999.00).recommended_action
        for risk, recoverability in [(15, 90), (45, 68), (55, 45), (82, 30)]
    }

    assert len(actions) >= 3


# --- authorisation: the binding guardrails ------------------------------


def test_normal_case_is_authorized():
    decision = authorize()

    assert decision.authorized is True
    assert decision.action == "retry_payment"
    assert decision.stop is False


def test_already_recovered_payment_stops():
    decision = authorize(payment_already_recovered=True)

    assert decision.authorized is False
    assert decision.stop is True
    assert decision.reason == "payment_already_recovered"


def test_retry_limit_stops_and_escalates():
    decision = authorize(retry_count=MAX_RETRIES)

    assert decision.authorized is False
    assert decision.escalate is True
    assert decision.stop is True
    assert decision.reason == "maximum_retry_limit_reached"


def test_high_risk_is_never_authorized_for_automation():
    # The agent may recommend anything; above the threshold the policy
    # refuses to authorise execution regardless.
    decision = authorize(
        recommended_action="retry_payment",
        risk_score=float(HIGH_RISK_THRESHOLD),
    )

    assert decision.authorized is False
    assert decision.escalate is True
    assert decision.reason == "high_risk_case"


def test_high_value_requires_policy_review():
    decision = authorize(amount_at_risk=HIGH_VALUE_THRESHOLD)

    assert decision.authorized is False
    assert decision.requires_review is True
    assert decision.reason == "high_value_requires_policy_review"


def test_retry_only_authorized_on_the_first_attempt():
    # Recoverability alone is not enough: a repeat attempt falls through
    # to a gentler strategy rather than retrying again.
    decision = authorize(recoverability_score=90.0, retry_count=1)

    assert decision.action == "send_reminder"


def test_moderate_recoverability_authorizes_reminder():
    decision = authorize(recoverability_score=65.0)

    assert decision.authorized is True
    assert decision.action == "send_reminder"


def test_low_recoverability_authorizes_payment_method_update():
    decision = authorize(recoverability_score=45.0)

    assert decision.authorized is True
    assert decision.action == "update_payment_method"


def test_very_low_recoverability_escalates():
    decision = authorize(recoverability_score=20.0)

    assert decision.authorized is False
    assert decision.escalate is True


def test_decision_records_the_factors_it_used():
    # These strings end up in the policy_checked audit event, so the
    # trail explains why the policy decided what it did.
    decision = authorize(risk_score=42.0, retry_count=1)

    joined = " ".join(decision.factors)

    assert "risk_score=42" in joined
    assert f"retry_count=1/{MAX_RETRIES}" in joined
