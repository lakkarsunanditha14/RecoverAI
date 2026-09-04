"""
Seed the database with demo payment data.

Run with:

    python -m app.simulator.seed

Idempotent: re-running updates the same rows instead of duplicating them.

The dataset is chosen so the recovery workflow produces a spread of
outcomes across every band of RecoveryDecisionPolicy (retry/high,
retry/medium, manual_review) rather than one repeated result.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.database import SessionLocal
from app.domain.payment import PaymentStatus
from app.domain.payment_attempt import AttemptStatus
from app.models.customer import CustomerModel
from app.models.payment import PaymentModel
from app.models.payment_attempt import PaymentAttemptModel


# (payment_id, customer_id, amount, payment_status, [attempt statuses])
PAYMENTS = [
    # Referenced by the integration tests; low risk -> retry_payment / high.
    (
        "pay_test_001",
        "cust_test_001",
        "4999.00",
        PaymentStatus.PENDING,
        [AttemptStatus.FAILED],
    ),
    # Single failed attempt -> retry_payment / medium.
    (
        "pay_1002",
        "cust_1002",
        "1299.00",
        PaymentStatus.FAILED,
        [AttemptStatus.FAILED],
    ),
    # Three failed attempts on a large amount -> manual_review.
    (
        "pay_1003",
        "cust_1003",
        "24999.00",
        PaymentStatus.FAILED,
        [AttemptStatus.FAILED, AttemptStatus.FAILED, AttemptStatus.FAILED],
    ),
    # Latest attempt status unknown -> manual_review.
    (
        "pay_1004",
        "cust_1004",
        "7499.00",
        PaymentStatus.FAILED,
        [AttemptStatus.FAILED, AttemptStatus.FAILED, AttemptStatus.UNKNOWN],
    ),
    # Still processing -> retry_payment / high.
    (
        "pay_1005",
        "cust_1005",
        "899.00",
        PaymentStatus.PENDING,
        [AttemptStatus.PROCESSING],
    ),
    # Two failed attempts -> retry_payment / medium.
    (
        "pay_1006",
        "cust_1006",
        "15750.00",
        PaymentStatus.FAILED,
        [AttemptStatus.FAILED, AttemptStatus.FAILED],
    ),
]


def seed() -> int:
    now = datetime.now(timezone.utc)
    db = SessionLocal()

    try:
        for age, (
            payment_id,
            customer_id,
            amount,
            payment_status,
            attempt_statuses,
        ) in enumerate(PAYMENTS):
            created_at = now - timedelta(days=age, hours=3)

            db.merge(
                CustomerModel(
                    customer_id=customer_id,
                    created_at=created_at - timedelta(days=30),
                )
            )

            db.merge(
                PaymentModel(
                    payment_id=payment_id,
                    customer_id=customer_id,
                    amount=Decimal(amount),
                    currency="INR",
                    status=payment_status,
                    created_at=created_at,
                )
            )

            for number, status in enumerate(attempt_statuses, start=1):
                db.merge(
                    PaymentAttemptModel(
                        attempt_id=f"attempt_{payment_id}_{number}",
                        payment_id=payment_id,
                        attempt_number=number,
                        amount=Decimal(amount),
                        status=status,
                        created_at=created_at + timedelta(minutes=number * 5),
                    )
                )

        db.commit()
    finally:
        db.close()

    return len(PAYMENTS)


if __name__ == "__main__":
    count = seed()
    print(f"Seeded {count} payments with customers and attempts.")
