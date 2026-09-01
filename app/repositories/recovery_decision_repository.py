from sqlalchemy.orm import Session

from app.domain.recovery_decision import RecoveryDecision
from app.models.recovery_decision import RecoveryDecisionModel


class RecoveryDecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, decision_id: str) -> RecoveryDecision | None:
        model = (
            self.db.query(RecoveryDecisionModel)
            .filter(RecoveryDecisionModel.decision_id == decision_id)
            .first()
        )

        if model is None:
            return None

        return RecoveryDecision(
            decision_id=model.decision_id,
            case_id=model.case_id,
            recommended_action=model.recommended_action,
            confidence=model.confidence,
            rationale=model.rationale,
            created_at=model.created_at,
        )

    def get_latest_by_case_id(self, case_id: str) -> RecoveryDecision | None:
        model = (
            self.db.query(RecoveryDecisionModel)
            .filter(RecoveryDecisionModel.case_id == case_id)
            .order_by(RecoveryDecisionModel.created_at.desc())
            .first()
        )

        if model is None:
            return None

        return RecoveryDecision(
            decision_id=model.decision_id,
            case_id=model.case_id,
            recommended_action=model.recommended_action,
            confidence=model.confidence,
            rationale=model.rationale,
            created_at=model.created_at,
        )

    def save(self, decision: RecoveryDecision) -> RecoveryDecision:
        model = RecoveryDecisionModel(
            decision_id=decision.decision_id,
            case_id=decision.case_id,
            recommended_action=decision.recommended_action,
            confidence=decision.confidence,
            rationale=decision.rationale,
            created_at=decision.created_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return RecoveryDecision(
            decision_id=model.decision_id,
            case_id=model.case_id,
            recommended_action=model.recommended_action,
            confidence=model.confidence,
            rationale=model.rationale,
            created_at=model.created_at,
        )
