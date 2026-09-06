from dataclasses import dataclass, field
from enum import StrEnum


class FailureCategory(StrEnum):
    """
    Why a payment failed, in terms a recovery strategy can act on.

    The categories are deliberately about *what to do next* rather than
    about provider error codes: two providers spell a declined card
    differently, but the recovery for both is the same.
    """

    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_EXPIRED = "card_expired"
    PAYMENT_METHOD_INVALID = "payment_method_invalid"
    BANK_TIMEOUT = "bank_timeout"
    GATEWAY_UNCERTAIN = "gateway_uncertain"
    PERSISTENT_DECLINE = "persistent_decline"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(frozen=True)
class Diagnosis:
    """
    A classification of why the revenue is at risk.

    Produced before the risk assessment and carried into the decision,
    so the chosen strategy answers the actual failure rather than
    treating every case as a candidate for another charge attempt.
    """

    category: FailureCategory
    confidence: str
    rationale: str
    # Whether charging the same instrument again could plausibly work.
    # An expired card will not start working because it was asked twice.
    retry_viable: bool
    signals: list[str] = field(default_factory=list)
