from decimal import Decimal

from app.agents.recovery_action_agent import RecoveryActionAgent
from app.domain.recovery_action import RecoveryActionType


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


def test_every_recommended_action_type_is_a_valid_action_type():
    # RecoveryActionService converts the agent's action_type into a
    # RecoveryActionType. A missing enum member surfaces as a 404 from the
    # API rather than an obvious error, so assert the conversion directly.
    agent = RecoveryActionAgent()

    for recommended_action in ["retry_payment", "manual_review", "unknown"]:
        result = agent.recommend(
            recommended_action=recommended_action,
            amount_at_risk=Decimal("4999.00"),
        )

        assert RecoveryActionType(result.action_type)
