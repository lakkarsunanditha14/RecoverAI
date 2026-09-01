from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Customer:
    customer_id: str
    created_at: datetime
