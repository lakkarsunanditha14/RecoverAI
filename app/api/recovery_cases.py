from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.repositories.recovery_outcome_repository import RecoveryOutcomeRepository
from app.repositories.risk_assessment_repository import RiskAssessmentRepository
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


@router.get("")
def list_recovery_cases(
    db: Session = Depends(get_db),
):
    cases = RecoveryCaseService(db).list_cases()
    risk_scores = RiskAssessmentRepository(db).get_latest_scores()
    recovered = RecoveryOutcomeRepository(db).get_recovered_totals()

    return [
        {
            "case_id": case.case_id,
            "payment_id": case.payment_id,
            "customer_id": case.customer_id,
            "amount_at_risk": str(case.amount_at_risk),
            "status": case.status,
            "created_at": case.created_at,
            # None until the case has been assessed, so the dashboard can
            # say so rather than inventing a risk band from the status.
            "risk_score": (risk_scores.get(case.case_id) or {}).get("risk"),
            "recoverability_score": (
                risk_scores.get(case.case_id) or {}
            ).get("recoverability"),
            # What actually came back, which for a partial
            # recovery is less than the amount at risk.
            "amount_recovered": str(recovered.get(case.case_id, 0)),
        }
        for case in cases
    ]


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
