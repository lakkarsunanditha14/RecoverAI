from sqlalchemy.orm import Session

from app.domain.recovery_case import RecoveryCase, RecoveryCaseStatus
from app.models.recovery_case import RecoveryCaseModel


class RecoveryCaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[RecoveryCase]:
        models = (
            self.db.query(RecoveryCaseModel)
            .order_by(RecoveryCaseModel.created_at.desc())
            .all()
        )

        return [
            RecoveryCase(
                case_id=model.case_id,
                payment_id=model.payment_id,
                customer_id=model.customer_id,
                amount_at_risk=model.amount_at_risk,
                status=RecoveryCaseStatus(model.status),
                created_at=model.created_at,
            )
            for model in models
        ]

    def get_by_id(self, case_id: str) -> RecoveryCase | None:
        model = (
            self.db.query(RecoveryCaseModel)
            .filter(RecoveryCaseModel.case_id == case_id)
            .first()
        )

        if model is None:
            return None

        return RecoveryCase(
            case_id=model.case_id,
            payment_id=model.payment_id,
            customer_id=model.customer_id,
            amount_at_risk=model.amount_at_risk,
            status=RecoveryCaseStatus(model.status),
            created_at=model.created_at,
        )

    def save(self, case: RecoveryCase) -> RecoveryCase:
        model = RecoveryCaseModel(
            case_id=case.case_id,
            payment_id=case.payment_id,
            customer_id=case.customer_id,
            amount_at_risk=case.amount_at_risk,
            status=case.status,
            created_at=case.created_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return RecoveryCase(
            case_id=model.case_id,
            payment_id=model.payment_id,
            customer_id=model.customer_id,
            amount_at_risk=model.amount_at_risk,
            status=RecoveryCaseStatus(model.status),
            created_at=model.created_at,
        )

    def update_status(
        self,
        case_id: str,
        status: RecoveryCaseStatus,
    ) -> RecoveryCase | None:
        model = (
            self.db.query(RecoveryCaseModel)
            .filter(RecoveryCaseModel.case_id == case_id)
            .first()
        )

        if model is None:
            return None

        model.status = status

        self.db.commit()
        self.db.refresh(model)

        return RecoveryCase(
            case_id=model.case_id,
            payment_id=model.payment_id,
            customer_id=model.customer_id,
            amount_at_risk=model.amount_at_risk,
            status=RecoveryCaseStatus(model.status),
            created_at=model.created_at,
        )
