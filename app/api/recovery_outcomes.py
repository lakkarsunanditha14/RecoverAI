from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.recovery_outcome import RecoveryOutcomeStatus
from app.services.recovery_outcome_service import RecoveryOutcomeService


router = APIRouter()


class RecoveryOutcomeRequest(BaseModel):
    action_id: str
    status: RecoveryOutcomeStatus
    amount_recovered: Decimal


class RecoveryOutcomeResponse(BaseModel):
    outcome_id: str
    case_id: str
    action_id: str
    status: RecoveryOutcomeStatus
    amount_recovered: Decimal
    recorded_at: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_response(outcome):
    return RecoveryOutcomeResponse(
        outcome_id=outcome.outcome_id,
        case_id=outcome.case_id,
        action_id=outcome.action_id,
        status=outcome.status,
        amount_recovered=outcome.amount_recovered,
        recorded_at=outcome.recorded_at.isoformat(),
    )


@router.get(
    "/recovery-cases/{case_id}/outcomes",
    response_model=list[RecoveryOutcomeResponse],
)
def get_recovery_case_outcomes(
    case_id: str,
    db: Session = Depends(get_db),
):
    try:
        outcomes = RecoveryOutcomeService(db).get_case_outcomes(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [build_response(outcome) for outcome in outcomes]


@router.post(
    "/recovery-cases/{case_id}/outcomes",
    response_model=RecoveryOutcomeResponse,
)
def record_recovery_outcome(
    case_id: str,
    request: RecoveryOutcomeRequest,
    db: Session = Depends(get_db),
):
    try:
        outcome = RecoveryOutcomeService(db).record_outcome(
            case_id=case_id,
            action_id=request.action_id,
            status=request.status,
            amount_recovered=request.amount_recovered,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return build_response(outcome)
