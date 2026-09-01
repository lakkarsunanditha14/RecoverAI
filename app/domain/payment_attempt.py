from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class AttemptStatus(StrEnum):
    CREATED = "created"
    PROCESSING = "processing"
    FAILED = "failed"
    SUCCESS = "success"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PaymentAttempt:
    attempt_id: str
    payment_id: str
    attempt_number: int
    amount: Decimal
    status: AttemptStatus
    created_at: datetime
