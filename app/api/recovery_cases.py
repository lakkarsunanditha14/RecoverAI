from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.recovery_case_service import RecoveryCaseService


router = APIRouter(
    prefix="/recovery-cases",
    tags=["Recovery Cases"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{payment_id}")
def create_recovery_case(
    payment_id: str,
    db: Session = Depends(get_db),
):
    try:
        case = RecoveryCaseService(db).create_case(payment_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return {
        "case_id": case.case_id,
        "payment_id": case.payment_id,
        "customer_id": case.customer_id,
        "amount_at_risk": str(case.amount_at_risk),
        "status": case.status,
        "created_at": case.created_at,
    }


@router.get("/{case_id}")
def get_recovery_case(
    case_id: str,
    db: Session = Depends(get_db),
):
    try:
        case = RecoveryCaseService(db).get_case(case_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return {
        "case_id": case.case_id,
        "payment_id": case.payment_id,
        "customer_id": case.customer_id,
        "amount_at_risk": str(case.amount_at_risk),
        "status": case.status,
        "created_at": case.created_at,
    }
