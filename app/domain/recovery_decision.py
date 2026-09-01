from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class DecisionConfidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class RecoveryDecision:
    decision_id: str
    case_id: str
    recommended_action: str
    confidence: DecisionConfidence
    rationale: str
    created_at: datetime
