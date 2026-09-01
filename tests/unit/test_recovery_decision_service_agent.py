from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.domain.recovery_case import RecoveryCaseStatus
from app.domain.recovery_decision import DecisionConfidence
from app.services.recovery_decision_service import RecoveryDecisionService


def make_case():
    return SimpleNamespace(
        case_id="case_test_001",
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount_at_risk=Decimal("4999.00"),
        status=RecoveryCaseStatus.CREATED,
    )


def make_assessment():
    return SimpleNamespace(
        assessment_id="risk_test_001",
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=80.0,
        recoverability_score=20.0,
    )


def test_service_uses_agent_recommendation():
    db = Mock()

    service = RecoveryDecisionService(db)

    service.recovery_case_repository = Mock()
    service.risk_assessment_repository = Mock()
    service.recovery_decision_repository = Mock()
    service.agent = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()
    service.risk_assessment_repository.get_latest_by_case_id.return_value = (
        make_assessment()
    )

    service.agent.decide.return_value = SimpleNamespace(
        recommended_action="manual_review",
        confidence="high",
        rationale="High recovery risk requires manual review.",
    )

    saved_decision = SimpleNamespace(
        decision_id="decision_test_001",
        case_id="case_test_001",
        recommended_action="manual_review",
        confidence=DecisionConfidence.HIGH,
        rationale="High recovery risk requires manual review.",
        created_at=Mock(),
    )

    service.recovery_decision_repository.save.return_value = saved_decision

    result = service.create_decision("case_test_001")

    service.agent.decide.assert_called_once_with(
        case_id="case_test_001",
        amount_at_risk=Decimal("4999.00"),
        risk_score=80.0,
        recoverability_score=20.0,
    )

    assert result.recommended_action == "manual_review"
    assert result.confidence == DecisionConfidence.HIGH
    assert result.rationale == "High recovery risk requires manual review."


def test_service_falls_back_when_no_assessment_exists():
    db = Mock()

    service = RecoveryDecisionService(db)

    service.recovery_case_repository = Mock()
    service.risk_assessment_repository = Mock()
    service.recovery_decision_repository = Mock()
    service.agent = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()
    service.risk_assessment_repository.get_latest_by_case_id.return_value = None

    saved_decision = SimpleNamespace(
        decision_id="decision_test_002",
        case_id="case_test_001",
        recommended_action="retry_payment",
        confidence=DecisionConfidence.MEDIUM,
        rationale="Recovery decision created for amount at risk 4999.00.",
        created_at=Mock(),
    )

    service.recovery_decision_repository.save.return_value = saved_decision

    result = service.create_decision("case_test_001")

    service.agent.decide.assert_not_called()

    assert result.recommended_action == "retry_payment"
    assert result.confidence == DecisionConfidence.MEDIUM
