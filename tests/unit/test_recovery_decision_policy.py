from app.policies.recovery_decision_policy import RecoveryDecisionPolicy


def test_low_risk_recommends_high_confidence_retry():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=20.0,
        recoverability_score=90.0,
        amount_at_risk=4999.00,
    )

    assert recommendation.recommended_action == "retry_payment"
    assert recommendation.confidence == "high"
    assert "Low recovery risk" in recommendation.rationale
    assert "4999.00" in recommendation.rationale


def test_moderate_risk_recommends_medium_confidence_retry():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=50.0,
        recoverability_score=70.0,
        amount_at_risk=4999.00,
    )

    assert recommendation.recommended_action == "retry_payment"
    assert recommendation.confidence == "medium"
    assert "Moderate recovery risk" in recommendation.rationale
    assert "4999.00" in recommendation.rationale


def test_high_risk_recommends_manual_review():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=80.0,
        recoverability_score=20.0,
        amount_at_risk=4999.00,
    )

    assert recommendation.recommended_action == "manual_review"
    assert recommendation.confidence == "high"
    assert "High recovery risk" in recommendation.rationale
    assert "4999.00" in recommendation.rationale


def test_high_risk_boundary_recommends_manual_review():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=70.0,
        recoverability_score=80.0,
        amount_at_risk=1000.00,
    )

    assert recommendation.recommended_action == "manual_review"
    assert recommendation.confidence == "high"


def test_low_recoverability_boundary_recommends_manual_review():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=20.0,
        recoverability_score=30.0,
        amount_at_risk=1000.00,
    )

    assert recommendation.recommended_action == "manual_review"
    assert recommendation.confidence == "high"


def test_moderate_risk_boundary_recommends_medium_confidence_retry():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=40.0,
        recoverability_score=80.0,
        amount_at_risk=1000.00,
    )

    assert recommendation.recommended_action == "retry_payment"
    assert recommendation.confidence == "medium"


def test_lower_recoverability_boundary_recommends_medium_confidence_retry():
    policy = RecoveryDecisionPolicy()

    recommendation = policy.recommend(
        risk_score=20.0,
        recoverability_score=60.0,
        amount_at_risk=1000.00,
    )

    assert recommendation.recommended_action == "retry_payment"
    assert recommendation.confidence == "medium"
