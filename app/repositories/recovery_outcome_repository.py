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
        # The latest outcome per case, not the sum of every outcome row.
        # A case has one authoritative result; summing the rows counts a
        # case twice when its outcome was recorded more than once, and can
        # report more money recovered than was ever at risk.
        latest = (
            self.db.query(RecoveryOutcomeModel)
            .distinct(RecoveryOutcomeModel.case_id)
            .order_by(
                RecoveryOutcomeModel.case_id,
                RecoveryOutcomeModel.recorded_at.desc(),
            )
            .all()
        )

        return {
            model.case_id: model.amount_recovered
            for model in latest
            if model.status in ("recovered", "partially_recovered")
        }

    def count_by_status(self) -> dict[str, int]:
        # Counts cases by their latest outcome, not outcome rows, so this
        # is comparable with the case counts instead of contradicting them.
        latest = (
            self.db.query(RecoveryOutcomeModel)
            .distinct(RecoveryOutcomeModel.case_id)
            .order_by(
                RecoveryOutcomeModel.case_id,
                RecoveryOutcomeModel.recorded_at.desc(),
            )
            .all()
        )

        counts: dict[str, int] = {}

        for model in latest:
            counts[model.status] = counts.get(model.status, 0) + 1

        return counts

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
