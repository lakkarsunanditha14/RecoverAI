from sqlalchemy.orm import Session

from app.domain.payment_attempt import PaymentAttempt
from app.models.payment_attempt import PaymentAttemptModel


class PaymentAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, attempt_id: str) -> PaymentAttempt | None:
        model = (
            self.db.query(PaymentAttemptModel)
            .filter(PaymentAttemptModel.attempt_id == attempt_id)
            .first()
        )

        if model is None:
            return None

        return PaymentAttempt(
            attempt_id=model.attempt_id,
            payment_id=model.payment_id,
            attempt_number=model.attempt_number,
            amount=model.amount,
            status=model.status,
            created_at=model.created_at,
        )

    def get_by_payment_id(self, payment_id: str) -> list[PaymentAttempt]:
        models = (
            self.db.query(PaymentAttemptModel)
            .filter(PaymentAttemptModel.payment_id == payment_id)
            .order_by(PaymentAttemptModel.attempt_number.asc())
            .all()
        )

        return [
            PaymentAttempt(
                attempt_id=model.attempt_id,
                payment_id=model.payment_id,
                attempt_number=model.attempt_number,
                amount=model.amount,
                status=model.status,
                created_at=model.created_at,
            )
            for model in models
        ]

    def save(self, attempt: PaymentAttempt) -> PaymentAttempt:
        model = PaymentAttemptModel(
            attempt_id=attempt.attempt_id,
            payment_id=attempt.payment_id,
            attempt_number=attempt.attempt_number,
            amount=attempt.amount,
            status=attempt.status,
            created_at=attempt.created_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return PaymentAttempt(
            attempt_id=model.attempt_id,
            payment_id=model.payment_id,
            attempt_number=model.attempt_number,
            amount=model.amount,
            status=model.status,
            created_at=model.created_at,
        )
