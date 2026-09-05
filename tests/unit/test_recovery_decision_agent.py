from decimal import Decimal

from app.agents.recovery_decision_agent import RecoveryDecisionAgent


def decide(risk_score, recoverability_score):
    return RecoveryDecisionAgent().decide(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=risk_score,
        recoverability_score=recoverability_score,
    )


def test_agent_returns_the_case_and_scores_it_was_given():
    result = decide(20.0, 90.0)

    assert result.case_id == "case_test_001"
    assert result.amount_at_risk == Decimal("4999.00")
    assert result.risk_score == 20.0
    assert result.recoverability_score == 90.0


def test_agent_recommends_retry_for_high_recoverability():
    result = decide(20.0, 90.0)

    assert result.recommended_action == "retry_payment"
    assert result.confidence == "high"


def test_agent_recommends_reminder_for_moderate_recoverability():
    result = decide(50.0, 70.0)

    assert result.recommended_action == "send_reminder"
    assert result.confidence == "medium"


def test_agent_recommends_escalation_for_high_risk():
    result = decide(80.0, 20.0)

    assert result.recommended_action == "escalate"
    assert result.confidence == "high"


def test_agent_preserves_policy_rationale():
    result = decide(80.0, 20.0)

    assert "human review" in result.rationale.lower()
    assert "4999.00" in result.rationale
