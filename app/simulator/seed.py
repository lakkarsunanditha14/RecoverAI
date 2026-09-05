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
#
# The scenarios are produced by the real pipeline, not asserted here:
# these payment and attempt shapes drive RiskAssessmentService, whose
# scores drive the policy, whose decision drives the simulator. The
# payment ids are chosen so the simulated outcomes are the ones each
# scenario needs — see tests for the expected spread.
_FAILED_ONCE = [AttemptStatus.FAILED]
_THREE_FAILED = [AttemptStatus.FAILED,
                 AttemptStatus.FAILED, AttemptStatus.FAILED]
_METHOD_ISSUE = [AttemptStatus.FAILED,
                 AttemptStatus.FAILED, AttemptStatus.UNKNOWN]

PAYMENTS = [
    # Referenced by the integration tests; must stay low risk.
    ("pay_test_001", "cust_test_001", "4999.00",
     PaymentStatus.PENDING, _FAILED_ONCE),

    # --- Low risk -> retry_payment, recovers on the first attempt -------
    ("pay_2004", "cust_2004", "899.00", PaymentStatus.PENDING, _FAILED_ONCE),
    ("pay_2005", "cust_2005", "1299.00", PaymentStatus.PENDING, _FAILED_ONCE),
    ("pay_2007", "cust_2007", "2450.00", PaymentStatus.PENDING, _FAILED_ONCE),
    ("pay_2009", "cust_2009", "3100.00", PaymentStatus.PENDING, _FAILED_ONCE),
    ("pay_2010", "cust_2010", "6750.00", PaymentStatus.PENDING, _FAILED_ONCE),

    # --- Medium risk -> send_reminder, recovers on a later attempt ------
    ("pay_2001", "cust_2001", "8400.00", PaymentStatus.PENDING, _THREE_FAILED),
    ("pay_2002", "cust_2002", "11200.00", PaymentStatus.PENDING, _THREE_FAILED),
    ("pay_2003", "cust_2003", "9800.00", PaymentStatus.PENDING, _THREE_FAILED),
    ("pay_2018", "cust_2018", "5300.00", PaymentStatus.PENDING, _THREE_FAILED),

    # --- Medium risk -> send_reminder, fails all three -> escalated -----
    # These three exercise the retry ladder to exhaustion.
    ("pay_2014", "cust_2014", "14600.00", PaymentStatus.PENDING, _THREE_FAILED),
    ("pay_2016", "cust_2016", "7250.00", PaymentStatus.PENDING, _THREE_FAILED),
    ("pay_2021", "cust_2021", "10400.00", PaymentStatus.PENDING, _THREE_FAILED),

    # --- Payment-method problem -> update_payment_method ----------------
    ("pay_2006", "cust_2006", "3600.00", PaymentStatus.PENDING, _METHOD_ISSUE),
    ("pay_2008", "cust_2008", "4150.00", PaymentStatus.PENDING, _METHOD_ISSUE),
    ("pay_2015", "cust_2015", "2900.00", PaymentStatus.PENDING, _METHOD_ISSUE),
    ("pay_2019", "cust_2019", "5850.00", PaymentStatus.PENDING, _METHOD_ISSUE),

    # --- High risk -> escalated by policy, nothing executed -------------
    ("pay_2011", "cust_2011", "24999.00", PaymentStatus.FAILED, _THREE_FAILED),
    ("pay_2012", "cust_2012", "18300.00", PaymentStatus.FAILED, _THREE_FAILED),
    ("pay_2013", "cust_2013", "31500.00", PaymentStatus.FAILED, _THREE_FAILED),
    ("pay_2017", "cust_2017", "15750.00", PaymentStatus.FAILED, _THREE_FAILED),

    # --- High value -> policy review before any automation --------------
    ("pay_2020", "cust_2020", "75000.00", PaymentStatus.PENDING, _FAILED_ONCE),
    ("pay_2022", "cust_2022", "120000.00", PaymentStatus.PENDING, _FAILED_ONCE),
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
