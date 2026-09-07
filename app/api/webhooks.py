from datetime import datetime, timezone
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.audit_event import AuditEvent, AuditEventType
from app.models.customer import CustomerModel
from app.models.payment import PaymentModel
from app.repositories.audit_event_repository import AuditEventRepository
from app.services.recovery_case_service import RecoveryCaseService

router = APIRouter(
    prefix="/webhooks",
    tags=["Webhooks"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class LivePaymentEvent(BaseModel):
    payment_id: Optional[str] = None
    customer_id: Optional[str] = "cust_live_merchant"
    customer_email: Optional[str] = "merchant_customer@example.com"
    amount: float = 4999.00
    failure_reason: Optional[str] = "Card authorization failed"


@router.post("/razorpay")
async def ingest_razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Ingest live Razorpay payment failure webhooks or live event payload.
    Creates Payment & Customer records in PostgreSQL, initializes Recovery Case,
    and logs audit events in real-time.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    event_type = body.get("event", "payment.failed")
    payload = body.get("payload", {}).get("payment", {}).get("entity", {})

    payment_id = (
        payload.get("id")
        or body.get("payment_id")
        or f"pay_live_{uuid.uuid4().hex[:8]}"
    )

    raw_amount = payload.get("amount")
    if raw_amount and raw_amount > 1000:
        amount = float(raw_amount) / 100.0
    else:
        amount = float(body.get("amount", 4999.00))

    customer_id = (
        body.get("customer_id")
        or payload.get("customer_id")
        or "cust_live_merchant"
    )
    failure_reason = (
        payload.get("error_description")
        or body.get("failure_reason")
        or "Payment authorization failed"
    )

    # 1. Ensure customer exists
    existing_cust = db.query(CustomerModel).filter(
        CustomerModel.customer_id == customer_id).first()
    if not existing_cust:
        new_cust = CustomerModel(
            customer_id=customer_id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_cust)
        db.flush()

    # 2. Ensure payment exists
    from decimal import Decimal
    existing_pay = db.query(PaymentModel).filter(
        PaymentModel.payment_id == payment_id).first()
    if not existing_pay:
        new_pay = PaymentModel(
            payment_id=payment_id,
            customer_id=customer_id,
            amount=Decimal(str(amount)),
            currency="INR",
            status="failed",
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_pay)
        db.flush()

    # 3. Create Recovery Case
    case_service = RecoveryCaseService(db)
    try:
        case = case_service.create_case(payment_id)
        case_id = case.case_id
    except ValueError:
        existing_case = case_service.get_case_by_payment_id(payment_id) if hasattr(
            case_service, "get_case_by_payment_id") else None
        case_id = existing_case.case_id if existing_case else f"case_{payment_id}"

    # 4. Log audit event
    audit_repo = AuditEventRepository(db)
    audit_repo.save(
        AuditEvent(
            event_id=f"event_{uuid.uuid4().hex}",
            case_id=case_id,
            event_type=AuditEventType.PAYMENT_FAILED,
            actor="razorpay_webhook",
            reason=f"Live Webhook: {event_type} - {failure_reason}",
            occurred_at=datetime.now(timezone.utc),
        )
    )

    db.commit()

    return {
        "status": "success",
        "message": "Razorpay payment failure webhook ingested successfully",
        "event_type": event_type,
        "payment_id": payment_id,
        "case_id": case_id,
        "amount_at_risk": amount,
        "mode": "live_ingestion",
    }
