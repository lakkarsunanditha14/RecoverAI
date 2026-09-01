from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.domain.payment import Payment, PaymentStatus
from app.domain.payment_attempt import AttemptStatus, PaymentAttempt
from app.domain.recovery_case import RecoveryCase, RecoveryCaseStatus
from app.domain.risk_assessment import RiskAssessment
from app.services.risk_assessment_service import RiskAssessmentService


class FakeRecoveryCaseRepository:
    def __init__(self, case):
        self.case = case

    def get_by_id(self, case_id):
        if self.case is not None and self.case.case_id == case_id:
            return self.case
        return None


class FakePaymentRepository:
    def __init__(self, payment):
        self.payment = payment

    def get_by_id(self, payment_id):
        if self.payment is not None and self.payment.payment_id == payment_id:
            return self.payment
        return None


class FakePaymentAttemptRepository:
    def __init__(self, attempts):
        self.attempts = attempts

    def get_by_payment_id(self, payment_id):
        return [
            attempt
            for attempt in self.attempts
            if attempt.payment_id == payment_id
        ]


class FakeRiskAssessmentRepository:
    def __init__(self):
        self.saved_assessments = []

    def save(self, assessment):
        self.saved_assessments.append(assessment)
        return assessment


def make_case():
    return RecoveryCase(
        case_id="case_test_001",
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount_at_risk=Decimal("4999.00"),
        status=RecoveryCaseStatus.CREATED,
        created_at=datetime.now(timezone.utc),
    )


def make_payment(status=PaymentStatus.FAILED):
    return Payment(
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount=Decimal("4999.00"),
        currency="INR",
        status=status,
        created_at=datetime.now(timezone.utc),
    )


def make_attempt(number, status):
    return PaymentAttempt(
        attempt_id=f"attempt_{number}",
        payment_id="pay_test_001",
        attempt_number=number,
        amount=Decimal("4999.00"),
        status=status,
        created_at=datetime.now(timezone.utc),
    )


def make_service(payment=None, case=None, attempts=None):
    service = RiskAssessmentService.__new__(RiskAssessmentService)

    service.payment_repository = FakePaymentRepository(payment)
    service.recovery_case_repository = FakeRecoveryCaseRepository(case)
    service.payment_attempt_repository = FakePaymentAttemptRepository(
        attempts or []
    )
    service.risk_assessment_repository = FakeRiskAssessmentRepository()

    return service


def test_failed_payment_produces_high_risk_signal():
    service = make_service(
        payment=make_payment(PaymentStatus.FAILED),
        case=make_case(),
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 40.0
    assert assessment.recoverability_score == 100.0
    assert "payment is failed" in assessment.reason


def test_multiple_failed_attempts_reduce_recoverability():
    attempts = [
        make_attempt(1, AttemptStatus.FAILED),
        make_attempt(2, AttemptStatus.FAILED),
    ]

    service = make_service(
        payment=make_payment(),
        case=make_case(),
        attempts=attempts,
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 60.0
    assert assessment.recoverability_score == 80.0
    assert "2 failed attempts recorded" in assessment.reason


def test_three_attempts_add_risk_and_reduce_recoverability():
    attempts = [
        make_attempt(1, AttemptStatus.FAILED),
        make_attempt(2, AttemptStatus.FAILED),
        make_attempt(3, AttemptStatus.FAILED),
    ]

    service = make_service(
        payment=make_payment(),
        case=make_case(),
        attempts=attempts,
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 80.0
    assert assessment.recoverability_score == 60.0
    assert "3 total attempts recorded" in assessment.reason


def test_unknown_latest_attempt_adds_risk():
    attempts = [
        make_attempt(1, AttemptStatus.FAILED),
        make_attempt(2, AttemptStatus.UNKNOWN),
    ]

    service = make_service(
        payment=make_payment(),
        case=make_case(),
        attempts=attempts,
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 50.0
    assert assessment.recoverability_score == 80.0
    assert "latest attempt status is unknown" in assessment.reason


def test_processing_latest_attempt_has_smaller_adjustment():
    attempts = [
        make_attempt(1, AttemptStatus.FAILED),
        make_attempt(2, AttemptStatus.PROCESSING),
    ]

    service = make_service(
        payment=make_payment(),
        case=make_case(),
        attempts=attempts,
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 45.0
    assert assessment.recoverability_score == 90.0
    assert "latest attempt is still processing" in assessment.reason


def test_no_negative_signals_keeps_baseline_scores():
    service = make_service(
        payment=make_payment(PaymentStatus.PENDING),
        case=make_case(),
        attempts=[
            make_attempt(1, AttemptStatus.CREATED),
        ],
    )

    assessment = service.assess("case_test_001")

    assert assessment.risk_score == 0.0
    assert assessment.recoverability_score == 100.0
    assert assessment.reason == "limited negative payment signals"


def test_assessment_is_saved_with_case_and_amount():
    repository = FakeRiskAssessmentRepository()

    service = RiskAssessmentService.__new__(RiskAssessmentService)
    service.payment_repository = FakePaymentRepository(make_payment())
    service.recovery_case_repository = FakeRecoveryCaseRepository(make_case())
    service.payment_attempt_repository = FakePaymentAttemptRepository([])
    service.risk_assessment_repository = repository

    assessment = service.assess("case_test_001")

    assert len(repository.saved_assessments) == 1
    assert repository.saved_assessments[0] is assessment
    assert assessment.case_id == "case_test_001"
    assert assessment.amount_at_risk == Decimal("4999.00")


def test_missing_case_raises_value_error():
    service = make_service(
        payment=make_payment(),
        case=None,
    )

    with pytest.raises(ValueError, match="Recovery case not found"):
        service.assess("case_test_001")


def test_missing_payment_raises_value_error():
    service = make_service(
        payment=None,
        case=make_case(),
    )

    with pytest.raises(ValueError, match="Payment not found"):
        service.assess("case_test_001")
