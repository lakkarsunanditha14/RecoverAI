from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AuditEventType(StrEnum):
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    RISK_ASSESSED = "risk_assessed"
    ACTION_PROPOSED = "action_proposed"
    POLICY_CHECKED = "policy_checked"
    ACTION_EXECUTED = "action_executed"
    OUTCOME_RECORDED = "outcome_recorded"
    CASE_ESCALATED = "case_escalated"
    CASE_STOPPED = "case_stopped"


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    case_id: str
    event_type: AuditEventType
    actor: str
    reason: str
    occurred_at: datetime
