from datetime import datetime, timezone
from decimal import Decimal

from app.domain.payment import Payment, PaymentStatus


def test_payment_can_be_created():
    payment = Payment(
        payment_id="pay_test_001",
        customer_id="cust_test_001",
        amount=Decimal("4999.00"),
        currency="INR",
        status=PaymentStatus.FAILED,
        created_at=datetime.now(timezone.utc),
    )

    assert payment.payment_id == "pay_test_001"
    assert payment.customer_id == "cust_test_001"
    assert payment.amount == Decimal("4999.00")
    assert payment.currency == "INR"
    assert payment.status == PaymentStatus.FAILED
