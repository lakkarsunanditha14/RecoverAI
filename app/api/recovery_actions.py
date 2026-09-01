from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.recovery_action import RecoveryActionType
from app.services.recovery_action_service import RecoveryActionService


router = APIRouter()


class RecoveryActionRequest(BaseModel):
    action_type: RecoveryActionType


class RecoveryActionResponse(BaseModel):
    action_id: str
    case_id: str
    action_type: RecoveryActionType
    status: str
    proposed_at: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/recovery-cases/{case_id}/actions",
    response_model=RecoveryActionResponse,
)
def propose_recovery_action(
    case_id: str,
    request: RecoveryActionRequest,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionService(db).propose_action(
            case_id=case_id,
            action_type=request.action_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return RecoveryActionResponse(
        action_id=action.action_id,
        case_id=action.case_id,
        action_type=action.action_type,
        status=action.status,
        proposed_at=action.proposed_at.isoformat(),
    )
