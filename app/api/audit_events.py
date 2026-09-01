from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.audit_event_service import AuditEventService


router = APIRouter()


class AuditEventRequest(BaseModel):
    event_type: str
    actor: str
    reason: str


class AuditEventResponse(BaseModel):
    event_id: str
    case_id: str
    event_type: str
    actor: str
    reason: str
    occurred_at: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_response(event):
    return AuditEventResponse(
        event_id=event.event_id,
        case_id=event.case_id,
        event_type=event.event_type,
        actor=event.actor,
        reason=event.reason,
        occurred_at=event.occurred_at.isoformat(),
    )


@router.post(
    "/recovery-cases/{case_id}/audit-events",
    response_model=AuditEventResponse,
)
def record_audit_event(
    case_id: str,
    request: AuditEventRequest,
    db: Session = Depends(get_db),
):
    try:
        event = AuditEventService(db).record_event(
            case_id=case_id,
            event_type=request.event_type,
            actor=request.actor,
            reason=request.reason,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return build_response(event)


@router.get(
    "/recovery-cases/{case_id}/audit-events",
    response_model=list[AuditEventResponse],
)
def get_recovery_case_audit_events(
    case_id: str,
    db: Session = Depends(get_db),
):
    try:
        events = AuditEventService(db).get_case_events(case_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    return [build_response(event) for event in events]
