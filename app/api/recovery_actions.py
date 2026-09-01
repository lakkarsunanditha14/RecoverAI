from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.recovery_action import RecoveryActionType
from app.services.recovery_action_execution_service import (
    RecoveryActionExecutionService,
)
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


def build_response(action):
    return RecoveryActionResponse(
        action_id=action.action_id,
        case_id=action.case_id,
        action_type=action.action_type,
        status=action.status,
        proposed_at=action.proposed_at.isoformat(),
    )


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
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)


@router.post(
    "/recovery-cases/{case_id}/ai-action",
    response_model=RecoveryActionResponse,
)
def propose_ai_recovery_action(
    case_id: str,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionService(db).propose_action(
            case_id=case_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)


@router.post(
    "/recovery-actions/{action_id}/approve",
    response_model=RecoveryActionResponse,
)
def approve_recovery_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionExecutionService(db).approve_action(
            action_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)


@router.post(
    "/recovery-actions/{action_id}/start",
    response_model=RecoveryActionResponse,
)
def start_recovery_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionExecutionService(db).start_execution(
            action_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)


@router.post(
    "/recovery-actions/{action_id}/complete",
    response_model=RecoveryActionResponse,
)
def complete_recovery_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionExecutionService(db).complete_action(
            action_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)


@router.post(
    "/recovery-actions/{action_id}/fail",
    response_model=RecoveryActionResponse,
)
def fail_recovery_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    try:
        action = RecoveryActionExecutionService(db).fail_action(
            action_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(action)
