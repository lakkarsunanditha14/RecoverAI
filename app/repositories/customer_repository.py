from sqlalchemy.orm import Session

from app.domain.customer import Customer
from app.models.customer import CustomerModel


class CustomerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, customer_id: str) -> Customer | None:
        model = (
            self.db.query(CustomerModel)
            .filter(CustomerModel.customer_id == customer_id)
            .first()
        )

        if model is None:
            return None

        return Customer(
            customer_id=model.customer_id,
            created_at=model.created_at,
        )

    def save(self, customer: Customer) -> Customer:
        model = CustomerModel(
            customer_id=customer.customer_id,
            created_at=customer.created_at,
        )

        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)

        return Customer(
            customer_id=model.customer_id,
            created_at=model.created_at,
        )
