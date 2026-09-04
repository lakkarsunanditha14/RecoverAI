from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.audit_event import AuditEventType
from app.domain.payment_attempt import AttemptStatus
from app.domain.payment import PaymentStatus
from app.domain.risk_assessment import RiskAssessment
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
from app.services.audit_event_service import AuditEventService


class RiskAssessmentService:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.payment_attempt_repository = PaymentAttemptRepository(db)
        self.risk_assessment_repository = RiskAssessmentRepository(db)
        self.audit_event_service = AuditEventService(db)

    def assess(self, case_id: str) -> RiskAssessment:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        payment = self.payment_repository.get_by_id(case.payment_id)

        if payment is None:
            raise ValueError(f"Payment not found: {case.payment_id}")

        attempts = self.payment_attempt_repository.get_by_payment_id(
            case.payment_id
        )

        risk_score = 0.0
        recoverability_score = 100.0
        reasons = []

        failed_attempts = [
            attempt
            for attempt in attempts
            if attempt.status == AttemptStatus.FAILED
        ]

        if payment.status == PaymentStatus.FAILED:
            risk_score += 40
            reasons.append("payment is failed")

        if len(failed_attempts) >= 2:
            risk_score += 20
            recoverability_score -= 20
            reasons.append(f"{len(failed_attempts)} failed attempts recorded")

        if len(attempts) >= 3:
            risk_score += 20
            recoverability_score -= 20
            reasons.append(f"{len(attempts)} total attempts recorded")

        if attempts:
            latest_attempt = attempts[-1]

            if latest_attempt.status == AttemptStatus.UNKNOWN:
                risk_score += 10
                recoverability_score -= 20
                reasons.append("latest attempt status is unknown")

            elif latest_attempt.status == AttemptStatus.PROCESSING:
                risk_score += 5
                recoverability_score -= 10
                reasons.append("latest attempt is still processing")

        risk_score = min(max(risk_score, 0.0), 100.0)
        recoverability_score = min(max(recoverability_score, 0.0), 100.0)

        if not reasons:
            reasons.append("limited negative payment signals")

        assessment = RiskAssessment(
            assessment_id=f"risk_{uuid4().hex}",
            case_id=case.case_id,
            amount_at_risk=case.amount_at_risk,
            risk_score=risk_score,
            recoverability_score=recoverability_score,
            reason="; ".join(reasons),
            assessed_at=datetime.now(timezone.utc),
        )

        saved_assessment = self.risk_assessment_repository.save(assessment)

        self.audit_event_service.record_event(
            case_id=case.case_id,
            event_type=AuditEventType.RISK_ASSESSED,
            actor="risk_assessment_service",
            reason=(
                f"Risk {risk_score:.0f}, recoverability "
                f"{recoverability_score:.0f}: {saved_assessment.reason}"
            ),
        )

        return saved_assessment
