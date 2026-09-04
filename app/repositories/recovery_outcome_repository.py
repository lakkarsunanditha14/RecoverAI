from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.recovery_outcome import RecoveryOutcome
from app.models.recovery_outcome import RecoveryOutcomeModel


class RecoveryOutcomeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, outcome_id: str) -> RecoveryOutcome | None:
        model = (
            self.db.query(RecoveryOutcomeModel)
            .filter(RecoveryOutcomeModel.outcome_id == outcome_id)
            .first()
        )

        if model is None:
            return None

        return self._to_domain(model)

    def get_by_case_id(self, case_id: str) -> list[RecoveryOutcome]:
        models = (
            self.db.query(RecoveryOutcomeModel)
            .filter(RecoveryOutcomeModel.case_id == case_id)
            .order_by(RecoveryOutcomeModel.recorded_at.asc())
            .all()
        )

        return [self._to_domain(model) for model in models]

    def get_recovered_totals(self) -> dict[str, Decimal]:
        # Summed per case in one query. A case can hold more than one
        # outcome, and a partial recovery brings back less than the amount
        # at risk, so the recovered figure has to come from the outcomes
        # rather than from the case's own amount.
        totals = (
            self.db.query(
                RecoveryOutcomeModel.case_id,
                func.sum(RecoveryOutcomeModel.amount_recovered),
            )
            .group_by(RecoveryOutcomeModel.case_id)
            .all()
        )

        return {case_id: total for case_id, total in totals}

    def save(self, outcome: RecoveryOutcome) -> RecoveryOutcome:
        model = RecoveryOutcomeModel(
            outcome_id=outcome.outcome_id,
            case_id=outcome.case_id,
            action_id=outcome.action_id,
            status=outcome.status,
            amount_recovered=outcome.amount_recovered,
            recorded_at=outcome.recorded_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return self._to_domain(model)

    @staticmethod
    def _to_domain(model: RecoveryOutcomeModel) -> RecoveryOutcome:
        return RecoveryOutcome(
            outcome_id=model.outcome_id,
            case_id=model.case_id,
            action_id=model.action_id,
            status=model.status,
            amount_recovered=model.amount_recovered,
            recorded_at=model.recorded_at,
        )
