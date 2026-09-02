from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domain.recovery_case import RecoveryCase, RecoveryCaseStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository


class RecoveryCaseService:
    def __init__(self, db: Session):
        self.db = db
        self.payment_repository = PaymentRepository(db)
        self.recovery_case_repository = RecoveryCaseRepository(db)

    def create_case(self, payment_id: str) -> RecoveryCase:
        payment = self.payment_repository.get_by_id(payment_id)

        if payment is None:
            raise ValueError(f"Payment not found: {payment_id}")

        case = RecoveryCase(
            case_id=f"case_{uuid4().hex}",
            payment_id=payment.payment_id,
            customer_id=payment.customer_id,
            amount_at_risk=Decimal(payment.amount),
            status=RecoveryCaseStatus.CREATED,
            created_at=datetime.now(timezone.utc),
        )

        return self.recovery_case_repository.save(case)

    def list_cases(self) -> list[RecoveryCase]:
        return self.recovery_case_repository.list_all()

    def get_case(self, case_id: str) -> RecoveryCase:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        return case

    def update_status(
        self,
        case_id: str,
        status: RecoveryCaseStatus,
    ) -> RecoveryCase:
        case = self.recovery_case_repository.update_status(
            case_id=case_id,
            status=status,
        )

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        return case
