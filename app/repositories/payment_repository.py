from sqlalchemy.orm import Session

from app.domain.payment import Payment
from app.models.payment import PaymentModel


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, payment_id: str) -> Payment | None:
        model = (
            self.db.query(PaymentModel)
            .filter(PaymentModel.payment_id == payment_id)
            .first()
        )

        if model is None:
            return None

        return Payment(
            payment_id=model.payment_id,
            customer_id=model.customer_id,
            amount=model.amount,
            currency=model.currency,
            status=model.status,
            created_at=model.created_at,
        )

    def save(self, payment: Payment) -> Payment:
        model = PaymentModel(
            payment_id=payment.payment_id,
            customer_id=payment.customer_id,
            amount=payment.amount,
            currency=payment.currency,
            status=payment.status,
            created_at=payment.created_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return Payment(
            payment_id=model.payment_id,
            customer_id=model.customer_id,
            amount=model.amount,
            currency=model.currency,
            status=model.status,
            created_at=model.created_at,
        )
