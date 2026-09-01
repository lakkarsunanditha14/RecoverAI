from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.risk_assessment_service import RiskAssessmentService


router = APIRouter(
    prefix="/recovery-cases",
    tags=["Risk Assessments"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{case_id}/risk-assessments")
def create_risk_assessment(
    case_id: str,
    db: Session = Depends(get_db),
):
    try:
        assessment = RiskAssessmentService(db).assess(case_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return {
        "assessment_id": assessment.assessment_id,
        "case_id": assessment.case_id,
        "amount_at_risk": str(assessment.amount_at_risk),
        "risk_score": assessment.risk_score,
        "recoverability_score": assessment.recoverability_score,
        "reason": assessment.reason,
        "assessed_at": assessment.assessed_at,
    }
