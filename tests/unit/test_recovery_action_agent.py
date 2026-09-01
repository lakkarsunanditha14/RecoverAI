from decimal import Decimal

from app.agents.recovery_action_agent import RecoveryActionAgent


def test_recommends_retry_payment():
    agent = RecoveryActionAgent()

    result = agent.recommend(
        recommended_action="retry_payment",
        amount_at_risk=Decimal("4999.00"),
    )

    assert result.action_type == "retry_payment"
    assert "4999.00" in result.rationale


def test_recommends_manual_review():
    agent = RecoveryActionAgent()

    result = agent.recommend(
        recommended_action="manual_review",
        amount_at_risk=Decimal("4999.00"),
    )

    assert result.action_type == "manual_review"
    assert "4999.00" in result.rationale


def test_unsupported_action_falls_back_to_manual_review():
    agent = RecoveryActionAgent()

    result = agent.recommend(
        recommended_action="unknown_action",
        amount_at_risk=Decimal("4999.00"),
    )

    assert result.action_type == "manual_review"
    assert "Unsupported recovery decision" in result.rationale
