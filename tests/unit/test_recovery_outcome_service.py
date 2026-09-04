from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

from app.domain.recovery_case import RecoveryCaseStatus
from app.domain.recovery_outcome import RecoveryOutcomeStatus
from app.services.recovery_outcome_service import RecoveryOutcomeService


def make_case():
    return SimpleNamespace(
        case_id="case_test_001",
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount_at_risk=Decimal("4999.00"),
        status="created",
    )


def make_action():
    return SimpleNamespace(
        action_id="action_test_001",
        case_id="case_test_001",
        action_type="retry_payment",
        status="proposed",
    )


def make_outcome(
    status=RecoveryOutcomeStatus.RECOVERED,
    amount_recovered=Decimal("4999.00"),
):
    return SimpleNamespace(
        outcome_id="outcome_test_001",
        case_id="case_test_001",
        action_id="action_test_001",
        status=status,
        amount_recovered=amount_recovered,
        recorded_at=Mock(),
    )


def test_service_records_recovered_outcome_and_updates_case():
    db = Mock()

    service = RecoveryOutcomeService(db)
    service.audit_event_service = Mock()

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.recovery_outcome_repository = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()
    service.recovery_action_repository.get_by_id.return_value = make_action()
    service.recovery_outcome_repository.save.return_value = make_outcome()

    result = service.record_outcome(
        case_id="case_test_001",
        action_id="action_test_001",
        status=RecoveryOutcomeStatus.RECOVERED,
        amount_recovered=Decimal("4999.00"),
    )

    assert result.status == RecoveryOutcomeStatus.RECOVERED
    assert result.amount_recovered == Decimal("4999.00")

    service.recovery_outcome_repository.save.assert_called_once()

    service.recovery_case_repository.update_status.assert_called_once_with(
        case_id="case_test_001",
        status=RecoveryCaseStatus.RECOVERED,
    )


def test_service_records_not_recovered_outcome_and_marks_case_failed():
    db = Mock()

    service = RecoveryOutcomeService(db)
    service.audit_event_service = Mock()

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.recovery_outcome_repository = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()
    service.recovery_action_repository.get_by_id.return_value = make_action()

    saved_outcome = SimpleNamespace(
        outcome_id="outcome_test_002",
        case_id="case_test_001",
        action_id="action_test_001",
        status=RecoveryOutcomeStatus.NOT_RECOVERED,
        amount_recovered=Decimal("0.00"),
        recorded_at=Mock(),
    )

    service.recovery_outcome_repository.save.return_value = saved_outcome

    result = service.record_outcome(
        case_id="case_test_001",
        action_id="action_test_001",
        status=RecoveryOutcomeStatus.NOT_RECOVERED,
        amount_recovered=Decimal("0.00"),
    )

    assert result.status == RecoveryOutcomeStatus.NOT_RECOVERED
    assert result.amount_recovered == Decimal("0.00")

    service.recovery_case_repository.update_status.assert_called_once_with(
        case_id="case_test_001",
        status=RecoveryCaseStatus.FAILED,
    )


def test_service_rejects_action_from_different_case():
    db = Mock()

    service = RecoveryOutcomeService(db)
    service.audit_event_service = Mock()

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.recovery_outcome_repository = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()

    service.recovery_action_repository.get_by_id.return_value = SimpleNamespace(
        action_id="action_other",
        case_id="case_other",
        action_type="retry_payment",
        status="proposed",
    )

    try:
        service.record_outcome(
            case_id="case_test_001",
            action_id="action_other",
            status=RecoveryOutcomeStatus.RECOVERED,
            amount_recovered=Decimal("4999.00"),
        )
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert str(exc) == (
            "Recovery action action_other does not belong to case case_test_001"
        )

    service.recovery_outcome_repository.save.assert_not_called()


def test_partial_recovery_updates_the_case_instead_of_leaving_it_created():
    # A partially recovered outcome used to fall through every branch, so
    # the outcome saved but the case kept its previous status and the
    # dashboard showed nothing had happened.
    db = Mock()

    service = RecoveryOutcomeService(db)
    service.audit_event_service = Mock()

    service.recovery_case_repository = Mock()
    service.recovery_action_repository = Mock()
    service.recovery_outcome_repository = Mock()

    service.recovery_case_repository.get_by_id.return_value = make_case()
    service.recovery_action_repository.get_by_id.return_value = make_action()
    service.recovery_outcome_repository.save.return_value = make_outcome(
        status=RecoveryOutcomeStatus.PARTIALLY_RECOVERED,
        amount_recovered=Decimal("1200.00"),
    )

    service.record_outcome(
        case_id="case_test_001",
        action_id="action_test_001",
        status=RecoveryOutcomeStatus.PARTIALLY_RECOVERED,
        amount_recovered=Decimal("1200.00"),
    )

    service.recovery_case_repository.update_status.assert_called_once_with(
        case_id="case_test_001",
        status=RecoveryCaseStatus.PARTIALLY_RECOVERED,
    )
