from sqlalchemy.orm import Session

from app.domain.risk_assessment import RiskAssessment
from app.models.risk_assessment import RiskAssessmentModel


class RiskAssessmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, assessment_id: str) -> RiskAssessment | None:
        model = (
            self.db.query(RiskAssessmentModel)
            .filter(RiskAssessmentModel.assessment_id == assessment_id)
            .first()
        )

        if model is None:
            return None

        return RiskAssessment(
            assessment_id=model.assessment_id,
            case_id=model.case_id,
            amount_at_risk=model.amount_at_risk,
            risk_score=model.risk_score,
            recoverability_score=model.recoverability_score,
            reason=model.reason,
            assessed_at=model.assessed_at,
        )

    def get_latest_by_case_id(self, case_id: str) -> RiskAssessment | None:
        model = (
            self.db.query(RiskAssessmentModel)
            .filter(RiskAssessmentModel.case_id == case_id)
            .order_by(RiskAssessmentModel.assessed_at.desc())
            .first()
        )

        if model is None:
            return None

        return RiskAssessment(
            assessment_id=model.assessment_id,
            case_id=model.case_id,
            amount_at_risk=model.amount_at_risk,
            risk_score=model.risk_score,
            recoverability_score=model.recoverability_score,
            reason=model.reason,
            assessed_at=model.assessed_at,
        )

    def get_latest_scores(self) -> dict[str, dict[str, float]]:
        # One row per case rather than a query per case, so listing cases
        # stays a fixed number of round trips as the case count grows.
        latest = (
            self.db.query(RiskAssessmentModel)
            .distinct(RiskAssessmentModel.case_id)
            .order_by(
                RiskAssessmentModel.case_id,
                RiskAssessmentModel.assessed_at.desc(),
            )
            .all()
        )

        return {
            model.case_id: {
                "risk": model.risk_score,
                "recoverability": model.recoverability_score,
            }
            for model in latest
        }

    def save(self, assessment: RiskAssessment) -> RiskAssessment:
        model = RiskAssessmentModel(
            assessment_id=assessment.assessment_id,
            case_id=assessment.case_id,
            amount_at_risk=assessment.amount_at_risk,
            risk_score=assessment.risk_score,
            recoverability_score=assessment.recoverability_score,
            reason=assessment.reason,
            assessed_at=assessment.assessed_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return RiskAssessment(
            assessment_id=model.assessment_id,
            case_id=model.case_id,
            amount_at_risk=model.amount_at_risk,
            risk_score=model.risk_score,
            recoverability_score=model.recoverability_score,
            reason=model.reason,
            assessed_at=model.assessed_at,
        )
