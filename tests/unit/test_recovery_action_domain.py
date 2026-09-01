from datetime import datetime, timezone

import pytest

from app.domain.recovery_action import (
    RecoveryAction,
    RecoveryActionStatus,
    RecoveryActionType,
)


def make_action(status=RecoveryActionStatus.PROPOSED):
    return RecoveryAction(
        action_id="action_test_001",
        case_id="case_test_001",
        action_type=RecoveryActionType.RETRY_PAYMENT,
        status=status,
        proposed_at=datetime.now(timezone.utc),
    )


def test_proposed_action_can_be_approved():
    action = make_action()

    approved = action.approve()

    assert approved.status == RecoveryActionStatus.APPROVED
    assert approved.action_id == action.action_id


def test_approved_action_can_start_execution():
    action = make_action().approve()

    executing = action.start_execution()

    assert executing.status == RecoveryActionStatus.EXECUTING


def test_executing_action_can_complete():
    action = make_action().approve().start_execution()

    completed = action.complete()

    assert completed.status == RecoveryActionStatus.COMPLETED


def test_executing_action_can_fail():
    action = make_action().approve().start_execution()

    failed = action.fail()

    assert failed.status == RecoveryActionStatus.FAILED


def test_proposed_action_cannot_start_execution_directly():
    action = make_action()

    with pytest.raises(ValueError):
        action.start_execution()


def test_proposed_action_cannot_complete():
    action = make_action()

    with pytest.raises(ValueError):
        action.complete()


def test_completed_action_cannot_be_completed_again():
    action = make_action().approve().start_execution().complete()

    with pytest.raises(ValueError):
        action.complete()
