from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RecoveryActionType(StrEnum):
    RETRY_PAYMENT = "retry_payment"
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
