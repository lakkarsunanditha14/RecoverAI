from decimal import Decimal

from app.domain.diagnosis import FailureCategory
from app.domain.payment_attempt import AttemptStatus, PaymentAttempt
from app.policies.recovery_decision_policy import RecoveryDecisionPolicy
from app.services.payment_diagnosis_service import PaymentDiagnosisService


def service():
    # The classifier needs no database; only diagnose() loads a case.
    return PaymentDiagnosisService.__new__(PaymentDiagnosisService)


def attempt(number, status, failure_reason=None):
    return PaymentAttempt(
        attempt_id=f"attempt_{number}",
        payment_id="pay_test_001",
        attempt_number=number,
        amount=Decimal("4999.00"),
        status=status,
        created_at=None,
        failure_reason=failure_reason,
    )


def failed(reason=None, count=1):
    return [attempt(i, AttemptStatus.FAILED, reason) for i in range(1, count + 1)]


# --- classification from the provider's reason --------------------------


def test_insufficient_funds_is_recognised():
    result = service()._classify(failed("insufficient_funds"))

    assert result.category == FailureCategory.INSUFFICIENT_FUNDS
    assert result.retry_viable is True


def test_expired_card_is_recognised_and_not_retryable():
    result = service()._classify(failed("card_expired"))

    assert result.category == FailureCategory.CARD_EXPIRED
    # No number of retries makes an expired card valid.
    assert result.retry_viable is False


def test_invalid_instrument_is_recognised():
    result = service()._classify(failed("do_not_honour"))

    assert result.category == FailureCategory.PAYMENT_METHOD_INVALID
    assert result.retry_viable is False


def test_bank_timeout_is_retryable():
    result = service()._classify(failed("bank_timeout"))

    assert result.category == FailureCategory.BANK_TIMEOUT
    assert result.retry_viable is True


def test_reason_variants_map_to_the_same_category():
    # Providers spell the same condition differently.
    assert (
        service()._classify(failed("low_balance")).category
        == service()._classify(failed("insufficient_funds")).category
    )


def test_repeating_a_reason_removes_retry_viability():
    once = service()._classify(failed("bank_timeout", count=1))
    thrice = service()._classify(failed("bank_timeout", count=3))

    assert once.retry_viable is True
    # A timeout seen three times is a settled fact, not a blip.
    assert thrice.retry_viable is False
    assert thrice.confidence == "high"


# --- fallback when no reason was recorded -------------------------------


def test_unresolved_final_attempt_is_uncertain():
    attempts = [attempt(1, AttemptStatus.FAILED), attempt(2, AttemptStatus.UNKNOWN)]

    result = service()._classify(attempts)

    assert result.category == FailureCategory.GATEWAY_UNCERTAIN
    # Whether the money moved is unknown, so retrying risks charging twice.
    assert result.retry_viable is False


def test_repeated_failures_without_a_reason_are_a_persistent_decline():
    result = service()._classify(failed(count=2))

    assert result.category == FailureCategory.PERSISTENT_DECLINE


def test_a_single_unexplained_failure_is_unknown():
    result = service()._classify(failed(count=1))

    assert result.category == FailureCategory.UNKNOWN_FAILURE


# --- the diagnosis must actually drive the strategy ---------------------


def test_diagnosis_changes_the_strategy_at_identical_scores():
    # Same risk and recoverability for every case, so any difference in
    # the chosen action comes from the diagnosis alone.
    policy = RecoveryDecisionPolicy()

    actions = {}
    for reason in ("bank_timeout", "card_expired", "insufficient_funds"):
        diagnosis = service()._classify(failed(reason))
        actions[reason] = policy.recommend(
            risk_score=20.0,
            recoverability_score=90.0,
            amount_at_risk=4999.00,
            diagnosis=diagnosis,
        ).recommended_action

    assert actions["bank_timeout"] == "retry_payment"
    assert actions["card_expired"] == "update_payment_method"
    assert actions["insufficient_funds"] == "send_reminder"


def test_policy_will_not_authorize_a_retry_that_cannot_work():
    # Recoverability alone would authorise a retry here; the diagnosis
    # says the instrument is expired, and that has to win.
    policy = RecoveryDecisionPolicy()
    diagnosis = service()._classify(failed("card_expired"))

    decision = policy.authorize(
        recommended_action="retry_payment",
        risk_score=20.0,
        recoverability_score=90.0,
        amount_at_risk=Decimal("4999.00"),
        retry_count=0,
        payment_already_recovered=False,
        diagnosis=diagnosis,
    )

    assert decision.action != "retry_payment"
    assert decision.action == "update_payment_method"
    assert decision.authorized is True


def test_guardrails_still_outrank_the_diagnosis():
    # A benign diagnosis must not talk the policy past a hard limit.
    policy = RecoveryDecisionPolicy()
    diagnosis = service()._classify(failed("bank_timeout"))

    decision = policy.authorize(
        recommended_action="retry_payment",
        risk_score=85.0,
        recoverability_score=90.0,
        amount_at_risk=Decimal("4999.00"),
        retry_count=0,
        payment_already_recovered=False,
        diagnosis=diagnosis,
    )

    assert decision.authorized is False
    assert decision.reason == "high_risk_case"
