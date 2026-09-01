from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.domain.recovery_action import (
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.services.recovery_action_service import RecoveryActionService


def make_case():
    return SimpleNamespace(
        case_id="case_test_001",
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount_at_risk=Decimal("4999.00"),
        status="created",
    )


def test_service_proposes_agent_recommended_action():
    db = Mock()

    service = RecoveryActionService(db)

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.agent = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()

    service.recovery_decision_repository = Mock()
    service.recovery_decision_repository.get_latest_by_case_id.return_value = (
        SimpleNamespace(
            recommended_action="retry_payment",
        )
    )

    service.agent.recommend.return_value = SimpleNamespace(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        confidence="high",
        rationale="Retry is recommended because recovery is favorable.",
    )

    saved_action = SimpleNamespace(
        action_id="action_test_001",
        case_id="case_test_001",
        action_type=RecoveryActionType.RETRY_PAYMENT,
        status=RecoveryActionStatus.PROPOSED,
        proposed_at=Mock(),
    )

    service.recovery_action_repository.save.return_value = saved_action

    result = service.propose_action("case_test_001")

    service.agent.recommend.assert_called_once_with(
        recommended_action="retry_payment",
        amount_at_risk=Decimal("4999.00"),
    )

    assert result.action_type == RecoveryActionType.RETRY_PAYMENT
    assert result.status == RecoveryActionStatus.PROPOSED


def test_service_falls_back_to_explicit_action_type():
    db = Mock()

    service = RecoveryActionService(db)

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.agent = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()

    saved_action = SimpleNamespace(
        action_id="action_test_002",
        case_id="case_test_001",
        action_type=RecoveryActionType.SEND_REMINDER,
        status=RecoveryActionStatus.PROPOSED,
        proposed_at=Mock(),
    )

    service.recovery_action_repository.save.return_value = saved_action

    result = service.propose_action(
        "case_test_001",
        RecoveryActionType.SEND_REMINDER,
    )

    service.agent.recommend.assert_not_called()

    assert result.action_type == RecoveryActionType.SEND_REMINDER
    assert result.status == RecoveryActionStatus.PROPOSED


def test_service_rejects_missing_case():
    db = Mock()

    service = RecoveryActionService(db)

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.agent = Mock()

    service.recovery_case_repository.get_by_id.return_value = None

    try:
        service.propose_action(
            "case_does_not_exist",
            RecoveryActionType.RETRY_PAYMENT,
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == "Recovery case not found: case_does_not_exist"

    service.recovery_action_repository.save.assert_not_called()
