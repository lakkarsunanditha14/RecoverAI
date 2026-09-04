from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RecoveryActionType(StrEnum):
    RETRY_PAYMENT = "retry_payment"
    MANUAL_REVIEW = "manual_review"
    SEND_REMINDER = "send_reminder"
    UPDATE_PAYMENT_METHOD = "update_payment_method"
    OFFER_ALTERNATIVE_METHOD = "offer_alternative_method"
    ESCALATE = "escalate"


class RecoveryActionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class RecoveryAction:
    action_id: str
    case_id: str
    action_type: RecoveryActionType
    status: RecoveryActionStatus
    proposed_at: datetime

    def approve(self) -> "RecoveryAction":
        if self.status != RecoveryActionStatus.PROPOSED:
            raise ValueError(
                f"Action {self.action_id} cannot be approved from status "
                f"{self.status}"
            )

        return RecoveryAction(
            action_id=self.action_id,
            case_id=self.case_id,
            action_type=self.action_type,
            status=RecoveryActionStatus.APPROVED,
            proposed_at=self.proposed_at,
        )

    def start_execution(self) -> "RecoveryAction":
        if self.status != RecoveryActionStatus.APPROVED:
            raise ValueError(
                f"Action {self.action_id} cannot start execution from status "
                f"{self.status}"
            )

        return RecoveryAction(
            action_id=self.action_id,
            case_id=self.case_id,
            action_type=self.action_type,
            status=RecoveryActionStatus.EXECUTING,
            proposed_at=self.proposed_at,
        )

    def complete(self) -> "RecoveryAction":
        if self.status != RecoveryActionStatus.EXECUTING:
            raise ValueError(
                f"Action {self.action_id} cannot be completed from status "
                f"{self.status}"
            )

        return RecoveryAction(
            action_id=self.action_id,
            case_id=self.case_id,
            action_type=self.action_type,
            status=RecoveryActionStatus.COMPLETED,
            proposed_at=self.proposed_at,
        )

    def fail(self) -> "RecoveryAction":
        if self.status != RecoveryActionStatus.EXECUTING:
            raise ValueError(
                f"Action {self.action_id} cannot fail from status "
                f"{self.status}"
            )

        return RecoveryAction(
            action_id=self.action_id,
            case_id=self.case_id,
            action_type=self.action_type,
            status=RecoveryActionStatus.FAILED,
            proposed_at=self.proposed_at,
        )
