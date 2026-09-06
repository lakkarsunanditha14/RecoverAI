from sqlalchemy.orm import Session

from app.domain.diagnosis import Diagnosis, FailureCategory
from app.domain.payment_attempt import AttemptStatus, PaymentAttempt
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository


# Provider reasons mapped onto the categories a recovery strategy can
# act on. Kept as substrings because providers spell the same condition
# several ways, and the mapping should not break on punctuation.
_REASON_PATTERNS: list[tuple[tuple[str, ...], FailureCategory, bool]] = [
    (("insufficient", "low_balance", "nsf"),
     FailureCategory.INSUFFICIENT_FUNDS, True),
    (("expired", "expiry"),
     FailureCategory.CARD_EXPIRED, False),
    (("invalid_card", "invalid_account", "card_not_supported",
      "do_not_honour", "do_not_honor", "blocked"),
     FailureCategory.PAYMENT_METHOD_INVALID, False),
    (("timeout", "timed_out", "unavailable", "issuer_down", "network"),
     FailureCategory.BANK_TIMEOUT, True),
]


class PaymentDiagnosisService:
    """
    Classifies why a payment is at risk.

    Deterministic on purpose: a recovery agent that spends money needs a
    diagnosis that can be reproduced and explained, not one that varies
    between runs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.recovery_case_repository = RecoveryCaseRepository(db)
        self.payment_repository = PaymentRepository(db)
        self.payment_attempt_repository = PaymentAttemptRepository(db)

    def diagnose(self, case_id: str) -> Diagnosis:
        case = self.recovery_case_repository.get_by_id(case_id)

        if case is None:
            raise ValueError(f"Recovery case not found: {case_id}")

        payment = self.payment_repository.get_by_id(case.payment_id)

        if payment is None:
            raise ValueError(f"Payment not found: {case.payment_id}")

        attempts = self.payment_attempt_repository.get_by_payment_id(
            case.payment_id
        )

        return self._classify(attempts)

    def _classify(self, attempts: list[PaymentAttempt]) -> Diagnosis:
        failed = [a for a in attempts if a.status == AttemptStatus.FAILED]
        latest = attempts[-1] if attempts else None

        signals = [f"{len(attempts)} attempts", f"{len(failed)} failed"]

        reason = self._latest_reason(attempts)

        if reason:
            signals.append(f"provider reason: {reason}")

            for patterns, category, retry_viable in _REASON_PATTERNS:
                if any(pattern in reason for pattern in patterns):
                    return self._from_reason(
                        category, reason, failed, signals, retry_viable
                    )

        # No usable reason, so fall back to the shape of the attempts.
        if latest and latest.status == AttemptStatus.UNKNOWN:
            return Diagnosis(
                category=FailureCategory.GATEWAY_UNCERTAIN,
                confidence="medium",
                rationale=(
                    "The provider never confirmed the final attempt, so "
                    "whether the money moved is unknown."
                ),
                retry_viable=False,
                signals=signals + ["latest attempt unresolved"],
            )

        if len(failed) >= 2:
            return Diagnosis(
                category=FailureCategory.PERSISTENT_DECLINE,
                confidence="medium",
                rationale=(
                    f"{len(failed)} attempts have been declined without a "
                    f"stated reason; the instrument is unlikely to clear "
                    f"on another identical attempt."
                ),
                retry_viable=False,
                signals=signals,
            )

        return Diagnosis(
            category=FailureCategory.UNKNOWN_FAILURE,
            confidence="low",
            rationale=(
                "No provider reason was recorded and the attempt history "
                "shows no clear pattern."
            ),
            retry_viable=True,
            signals=signals,
        )

    def _from_reason(
        self,
        category: FailureCategory,
        reason: str,
        failed: list[PaymentAttempt],
        signals: list[str],
        retry_viable: bool,
    ) -> Diagnosis:
        # A reason repeated across attempts is a settled fact rather than
        # a one-off, so retrying the same instrument stops being viable.
        repeated = len(failed) >= 2

        rationales = {
            FailureCategory.INSUFFICIENT_FUNDS: (
                "The account did not hold the amount at the time of the "
                "attempt; the balance may change, but charging again "
                "immediately will not."
            ),
            FailureCategory.CARD_EXPIRED: (
                "The instrument is expired. No number of retries will "
                "make it valid; the customer has to supply a new one."
            ),
            FailureCategory.PAYMENT_METHOD_INVALID: (
                "The provider rejected the instrument itself rather than "
                "the transaction, so a different method is required."
            ),
            FailureCategory.BANK_TIMEOUT: (
                "The failure came from the network or the issuer rather "
                "than the customer, which is the case most likely to "
                "clear on a straight retry."
            ),
        }

        return Diagnosis(
            category=category,
            confidence="high" if repeated else "medium",
            rationale=rationales[category],
            retry_viable=retry_viable and not repeated,
            signals=signals + ([f"reason seen on {len(failed)} attempts"]
                               if repeated else []),
        )

    @staticmethod
    def _latest_reason(attempts: list[PaymentAttempt]) -> str | None:
        for attempt in reversed(attempts):
            if attempt.failure_reason:
                return attempt.failure_reason.strip().lower()

        return None
