from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.domain.recovery_action import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.services.recovery_action_execution_service import (
    RecoveryActionExecutionService,
)


def make_action(status=RecoveryActionStatus.PROPOSED):
    return RecoveryAction(
        action_id="action_test_001",
        case_id="case_test_001",
        action_type=RecoveryActionType.RETRY_PAYMENT,
        status=status,
        proposed_at=datetime.now(timezone.utc),
    )


def make_service(action):
    db = Mock()

    service = RecoveryActionExecutionService(db)
    service.recovery_action_repository = Mock()

    service.recovery_action_repository.get_by_id.return_value = action
    service.recovery_action_repository.update.side_effect = lambda value: value

    return service


def test_service_approves_action():
    service = make_service(make_action())

    result = service.approve_action("action_test_001")

    assert result.status == RecoveryActionStatus.APPROVED

    service.recovery_action_repository.get_by_id.assert_called_once_with(
        "action_test_001"
    )
    service.recovery_action_repository.update.assert_called_once()


def test_service_starts_execution():
    service = make_service(
        make_action(RecoveryActionStatus.APPROVED)
    )

    result = service.start_execution("action_test_001")

    assert result.status == RecoveryActionStatus.EXECUTING


def test_service_completes_action():
    service = make_service(
        make_action(RecoveryActionStatus.EXECUTING)
    )

    result = service.complete_action("action_test_001")

    assert result.status == RecoveryActionStatus.COMPLETED


def test_service_fails_action():
    service = make_service(
        make_action(RecoveryActionStatus.EXECUTING)
    )

    result = service.fail_action("action_test_001")

    assert result.status == RecoveryActionStatus.FAILED


def test_service_rejects_missing_action():
    db = Mock()

    service = RecoveryActionExecutionService(db)
    service.recovery_action_repository = Mock()
    service.recovery_action_repository.get_by_id.return_value = None

    with pytest.raises(ValueError) as exc:
        service.approve_action("action_does_not_exist")

    assert str(exc.value) == (
        "Recovery action not found: action_does_not_exist"
    )

    service.recovery_action_repository.update.assert_not_called()
