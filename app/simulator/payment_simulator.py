"""
Simulated payment verification for the recovery agent.

TEST SIMULATION. No payment provider is contacted and no real money
moves. The result is derived deterministically from the case, the
attempt number and the assessed recoverability, so a demo replays
identically rather than flipping between runs.
"""

from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class SimulatedPaymentResult:
    succeeded: bool
    detail: str
    mode: str = "test_simulation"


def verify_payment(
    payment_id: str,
    attempt_number: int,
    recoverability_score: float,
) -> SimulatedPaymentResult:
    # Keyed on the payment, not the case: case ids are uuids minted on
    # every reset, which made the same demo produce different outcomes
    # each run. The payment id is stable, so the batch replays exactly.
    digest = sha256(f"{payment_id}:{attempt_number}".encode()).hexdigest()
    roll = int(digest[:8], 16) % 100

    # Later attempts are less likely to succeed than the first.
    threshold = max(recoverability_score - (attempt_number - 1) * 20, 0)
    succeeded = roll < threshold

    if succeeded:
        detail = (
            f"Simulated payment succeeded on attempt {attempt_number} "
            f"(roll {roll} < threshold {threshold:.0f})."
        )
    else:
        detail = (
            f"Simulated payment failed on attempt {attempt_number} "
            f"(roll {roll} >= threshold {threshold:.0f})."
        )

    return SimulatedPaymentResult(succeeded=succeeded, detail=detail)
