from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class RiskAssessment:
    assessment_id: str
    case_id: str
    amount_at_risk: Decimal
    risk_score: float
    recoverability_score: float
    reason: str
    assessed_at: datetime
