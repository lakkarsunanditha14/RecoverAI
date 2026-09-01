from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class RecoveryOutcomeStatus(StrEnum):
    RECOVERED = "recovered"
    PARTIALLY_RECOVERED = "partially_recovered"
    NOT_RECOVERED = "not_recovered"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RecoveryOutcome:
    outcome_id: str
    case_id: str
    action_id: str
    status: RecoveryOutcomeStatus
    amount_recovered: Decimal
    recorded_at: datetime
