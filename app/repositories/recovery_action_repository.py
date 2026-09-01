from sqlalchemy.orm import Session

from app.domain.recovery_action import RecoveryAction
from app.models.recovery_action import RecoveryActionModel


class RecoveryActionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, action_id: str) -> RecoveryAction | None:
        model = (
            self.db.query(RecoveryActionModel)
            .filter(RecoveryActionModel.action_id == action_id)
            .first()
        )

        if model is None:
            return None

        return RecoveryAction(
            action_id=model.action_id,
            case_id=model.case_id,
            action_type=model.action_type,
            status=model.status,
            proposed_at=model.proposed_at,
        )

    def save(self, action: RecoveryAction) -> RecoveryAction:
        model = RecoveryActionModel(
            action_id=action.action_id,
            case_id=action.case_id,
            action_type=action.action_type,
            status=action.status,
            proposed_at=action.proposed_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return RecoveryAction(
            action_id=model.action_id,
            case_id=model.case_id,
            action_type=model.action_type,
            status=model.status,
            proposed_at=model.proposed_at,
        )
