from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEventType
from app.domain.recovery_action import RecoveryActionType
from app.domain.recovery_case import RecoveryCaseStatus
from app.domain.recovery_outcome import RecoveryOutcomeStatus
from app.policies.recovery_decision_policy import (
    MAX_RETRIES,
    RecoveryDecisionPolicy,
)
from app.repositories.recovery_action_repository import RecoveryActionRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.services.audit_event_service import AuditEventService
from app.services.recovery_action_execution_service import (
    RecoveryActionExecutionService,
)
from app.services.recovery_action_service import RecoveryActionService
from app.services.recovery_decision_service import RecoveryDecisionService
from app.services.recovery_outcome_service import RecoveryOutcomeService
from app.services.risk_assessment_service import RiskAssessmentService
from app.simulator.payment_simulator import verify_payment


@dataclass
class OrchestrationResult:
    case_id: str
    status: str
    risk_score: float = 0.0
    recoverability_score: float = 0.0
    recommended_action: str = ""
    policy_decision: str = ""
    execution_status: str = "not_executed"
    attempt_number: int = 0
    max_attempts: int = MAX_RETRIES
    amount_at_risk: float = 0.0
    amount_recovered: float = 0.0
    escalated: bool = False
    stopped: bool = False
    stop_reason: str = ""
    audit_event_ids: list[str] = field(default_factory=list)
    mode: str = "test_simulation"


class RecoveryOrchestratorService:
    """
    Runs the whole loop for one case: assess, decide, authorise, execute,
    verify, record, then stop or escalate.

    The agent recommends and the policy authorises. Execution only
    happens for an action the policy returned as authorised.
    """

    def __init__(self, db: Session):
        self.db = db
        self.case_repository = RecoveryCaseRepository(db)
        self.action_repository = RecoveryActionRepository(db)
        self.risk_service = RiskAssessmentService(db)
        self.decision_service = RecoveryDecisionService(db)
        self.action_service = RecoveryActionService(db)
        self.execution_service = RecoveryActionExecutionService(db)
        self.outcome_service = RecoveryOutcomeService(db)
        self.audit_service = AuditEventService(db)
        self.policy = RecoveryDecisionPolicy()

    def run(self, case_id: str) -> OrchestrationResult:
        case = self.case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        result = OrchestrationResult(
            case_id=case.case_id,
            status=str(case.status),
            amount_at_risk=float(case.amount_at_risk),
        )

        if case.status in {
            RecoveryCaseStatus.RECOVERED,
            RecoveryCaseStatus.PARTIALLY_RECOVERED,
            RecoveryCaseStatus.ESCALATED,
            RecoveryCaseStatus.FAILED,
            RecoveryCaseStatus.STOPPED,
        }:
            result.stopped = True
            result.stop_reason = "case_already_closed"
            result.policy_decision = "stop"
            return result

        assessment = self.risk_service.assess(case.case_id)
        result.risk_score = float(assessment.risk_score)
        result.recoverability_score = float(assessment.recoverability_score)

        decision = self.decision_service.create_decision(case_id=case.case_id)
        result.recommended_action = str(decision.recommended_action)

        self._audit(
            result,
            case.case_id,
            AuditEventType.DECISION_GENERATED,
            "recovery_decision_agent",
            f"Agent recommended {decision.recommended_action} "
            f"({decision.confidence}).",
        )

        retry_count = len(
            self.action_repository.list_by_case_id(case.case_id)
        )

        policy_result = self.policy.authorize(
            recommended_action=str(decision.recommended_action),
            risk_score=result.risk_score,
            recoverability_score=result.recoverability_score,
            amount_at_risk=case.amount_at_risk,
            retry_count=retry_count,
            payment_already_recovered=False,
        )

        result.policy_decision = policy_result.action
        result.attempt_number = retry_count

        self._audit(
            result,
            case.case_id,
            AuditEventType.POLICY_CHECKED,
            "recovery_decision_policy",
            f"{policy_result.reason} | " + " ".join(policy_result.factors),
        )

        if not policy_result.authorized:
            return self._halt(result, case.case_id, policy_result)

        return self._execute_attempts(result, case, policy_result)

    def _execute_attempts(self, result, case, policy_result):
        attempt = result.attempt_number

        while attempt < MAX_RETRIES:
            attempt += 1
            result.attempt_number = attempt

            action = self.action_service.propose_action(
                case_id=case.case_id,
                action_type=RecoveryActionType(policy_result.action),
            )

            self._audit(
                result,
                case.case_id,
                AuditEventType.ACTION_AUTHORIZED,
                "recovery_decision_policy",
                f"Attempt {attempt}/{MAX_RETRIES}: {policy_result.action} "
                f"authorized ({policy_result.reason}).",
            )

            self.execution_service.approve_action(action.action_id)
            self.execution_service.start_execution(action.action_id)

            payment = verify_payment(
                payment_id=case.payment_id,
                attempt_number=attempt,
                recoverability_score=result.recoverability_score,
            )

            if payment.succeeded:
                self.execution_service.complete_action(action.action_id)
                result.execution_status = "completed"

                self._audit(
                    result,
                    case.case_id,
                    AuditEventType.PAYMENT_VERIFIED,
                    "payment_simulator",
                    f"TEST SIMULATION: {payment.detail}",
                )

                self.outcome_service.record_outcome(
                    case_id=case.case_id,
                    action_id=action.action_id,
                    status=RecoveryOutcomeStatus.RECOVERED,
                    amount_recovered=case.amount_at_risk,
                )

                result.amount_recovered = float(case.amount_at_risk)
                result.stopped = True
                result.stop_reason = "payment_recovered"
                result.status = str(RecoveryCaseStatus.RECOVERED)

                self._audit(
                    result,
                    case.case_id,
                    AuditEventType.CASE_STOPPED,
                    "orchestrator",
                    "Recovered; automation stopped.",
                )
                return result

            self.execution_service.fail_action(action.action_id)
            result.execution_status = "failed"

            self._audit(
                result,
                case.case_id,
                AuditEventType.PAYMENT_FAILED,
                "payment_simulator",
                f"TEST SIMULATION: {payment.detail}",
            )

            if attempt < MAX_RETRIES:
                self._audit(
                    result,
                    case.case_id,
                    AuditEventType.RETRY_ATTEMPTED,
                    "orchestrator",
                    f"Attempt {attempt} failed; retrying "
                    f"({attempt + 1}/{MAX_RETRIES}).",
                )

        # Every attempt failed.
        self._audit(
            result,
            case.case_id,
            AuditEventType.RETRY_LIMIT_REACHED,
            "orchestrator",
            f"All {MAX_RETRIES} attempts failed.",
        )

        self.outcome_service.record_outcome(
            case_id=case.case_id,
            action_id=self.action_repository.list_by_case_id(
                case.case_id
            )[-1].action_id,
            status=RecoveryOutcomeStatus.NOT_RECOVERED,
            amount_recovered=Decimal("0.00"),
        )

        self.case_repository.update_status(
            case_id=case.case_id,
            status=RecoveryCaseStatus.ESCALATED,
        )

        result.escalated = True
        result.stopped = True
        result.stop_reason = "maximum_retry_limit_reached"
        result.status = str(RecoveryCaseStatus.ESCALATED)

        self._audit(
            result,
            case.case_id,
            AuditEventType.CASE_ESCALATED,
            "orchestrator",
            "Retry limit reached; escalated for human review.",
        )
        return result

    def _halt(self, result, case_id, policy_result):
        result.stopped = policy_result.stop
        result.stop_reason = policy_result.reason
        result.escalated = policy_result.escalate

        if policy_result.escalate:
            self.case_repository.update_status(
                case_id=case_id,
                status=RecoveryCaseStatus.ESCALATED,
            )
            result.status = str(RecoveryCaseStatus.ESCALATED)
            self._audit(
                result,
                case_id,
                AuditEventType.CASE_ESCALATED,
                "recovery_decision_policy",
                f"Escalated without execution: {policy_result.reason}.",
            )
        else:
            self.case_repository.update_status(
                case_id=case_id,
                status=RecoveryCaseStatus.STOPPED,
            )
            result.status = str(RecoveryCaseStatus.STOPPED)
            self._audit(
                result,
                case_id,
                AuditEventType.CASE_STOPPED,
                "recovery_decision_policy",
                f"Stopped without execution: {policy_result.reason}.",
            )

        return result

    def _audit(self, result, case_id, event_type, actor, reason):
        event = self.audit_service.record_event(
            case_id=case_id,
            event_type=event_type,
            actor=actor,
            reason=reason,
        )
        result.audit_event_ids.append(event.event_id)
        return event
