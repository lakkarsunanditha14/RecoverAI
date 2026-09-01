from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.recovery_decision import DecisionConfidence
from app.services.recovery_decision_service import RecoveryDecisionService


router = APIRouter()


class RecoveryDecisionRequest(BaseModel):
    recommended_action: str
    confidence: DecisionConfidence
    rationale: str


class RecoveryDecisionResponse(BaseModel):
    decision_id: str
    case_id: str
    recommended_action: str
    confidence: DecisionConfidence
    rationale: str
    created_at: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/recovery-cases/{case_id}/decisions",
    response_model=RecoveryDecisionResponse,
)
def create_recovery_decision(
    case_id: str,
    request: RecoveryDecisionRequest,
    db: Session = Depends(get_db),
):
    try:
        decision = RecoveryDecisionService(db).create_decision(
            case_id=case_id,
            recommended_action=request.recommended_action,
            confidence=request.confidence,
            rationale=request.rationale,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return RecoveryDecisionResponse(
        decision_id=decision.decision_id,
        case_id=decision.case_id,
        recommended_action=decision.recommended_action,
        confidence=decision.confidence,
        rationale=decision.rationale,
        created_at=decision.created_at.isoformat(),
    )
