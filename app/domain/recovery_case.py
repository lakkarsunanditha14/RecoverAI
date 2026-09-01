from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class RecoveryCaseStatus(StrEnum):
    CREATED = "created"
    INVESTIGATING = "investigating"
    DECISION_READY = "decision_ready"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RECOVERED = "recovered"
    FAILED = "failed"
    STOPPED = "stopped"
    ESCALATED = "escalated"


@dataclass(frozen=True)
class RecoveryCase:
    case_id: str
    payment_id: str
    customer_id: str
    amount_at_risk: Decimal
    status: RecoveryCaseStatus
    created_at: datetime
