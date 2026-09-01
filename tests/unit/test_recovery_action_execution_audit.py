from datetime import datetime, timezone
from unittest.mock import Mock

from app.domain.recovery_action import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)
from app.services.recovery_action_execution_service import (
    RecoveryActionExecutionService,
)


def make_action(status):
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

    service.audit_event_repository = Mock()

    return service


def test_approve_records_audit_event():
    service = make_service(make_action(RecoveryActionStatus.PROPOSED))

    result = service.approve_action("action_test_001")

    assert result.status == RecoveryActionStatus.APPROVED
    service.audit_event_repository.save.assert_called_once()

    event = service.audit_event_repository.save.call_args.args[0]

    assert event.case_id == "case_test_001"
    assert event.event_type == "action_executed"
    assert event.actor == "recovery_action_service"
    assert event.reason == "Recovery action approved."


def test_start_execution_records_audit_event():
    service = make_service(make_action(RecoveryActionStatus.APPROVED))

    result = service.start_execution("action_test_001")

    assert result.status == RecoveryActionStatus.EXECUTING
    service.audit_event_repository.save.assert_called_once()


def test_complete_records_audit_event():
    service = make_service(make_action(RecoveryActionStatus.EXECUTING))

    result = service.complete_action("action_test_001")

    assert result.status == RecoveryActionStatus.COMPLETED
    service.audit_event_repository.save.assert_called_once()


def test_fail_records_audit_event():
    service = make_service(make_action(RecoveryActionStatus.EXECUTING))

    result = service.fail_action("action_test_001")

    assert result.status == RecoveryActionStatus.FAILED
    service.audit_event_repository.save.assert_called_once()
