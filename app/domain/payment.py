from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class PaymentStatus(StrEnum):
    PENDING = "pending"
    FAILED = "failed"
    SUCCESS = "success"


@dataclass(frozen=True)
class Payment:
    payment_id: str
    customer_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    created_at: datetime
