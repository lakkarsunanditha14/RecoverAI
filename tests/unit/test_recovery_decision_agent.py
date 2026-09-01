from decimal import Decimal

from app.agents.recovery_decision_agent import RecoveryDecisionAgent


def test_agent_recommends_retry_for_low_risk():
    agent = RecoveryDecisionAgent()

    result = agent.decide(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=20.0,
        recoverability_score=90.0,
    )

    assert result.case_id == "case_test_001"
    assert result.amount_at_risk == Decimal("4999.00")
    assert result.risk_score == 20.0
    assert result.recoverability_score == 90.0
    assert result.recommended_action == "retry_payment"
    assert result.confidence == "high"


def test_agent_recommends_retry_for_moderate_risk():
    agent = RecoveryDecisionAgent()

    result = agent.decide(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=50.0,
        recoverability_score=70.0,
    )

    assert result.recommended_action == "retry_payment"
    assert result.confidence == "medium"


def test_agent_recommends_manual_review_for_high_risk():
    agent = RecoveryDecisionAgent()

    result = agent.decide(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=80.0,
        recoverability_score=20.0,
    )

    assert result.recommended_action == "manual_review"
    assert result.confidence == "high"


def test_agent_preserves_policy_rationale():
    agent = RecoveryDecisionAgent()

    result = agent.decide(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=80.0,
        recoverability_score=20.0,
    )

    assert "manual review" in result.rationale.lower()
    assert "4999.00" in result.rationale
