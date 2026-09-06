from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.domain.recovery_case import RecoveryCaseStatus
from app.policies.recovery_decision_policy import (
    RecoveryDecisionPolicy,
    HIGH_RISK_THRESHOLD,
    HIGH_VALUE_THRESHOLD,
    MAX_RETRIES,
    RECOVERY_WINDOW_DAYS,
)
from app.repositories.recovery_action_repository import RecoveryActionRepository
from app.repositories.recovery_case_repository import RecoveryCaseRepository
from app.repositories.recovery_outcome_repository import (
    RecoveryOutcomeRepository,
)
from app.repositories.risk_assessment_repository import (
    RiskAssessmentRepository,
)
from app.services.recovery_orchestrator_service import (
    RecoveryOrchestratorService,
)

router = APIRouter()


# A case in one of these states is finished; the agent has nothing left
# to do with it and it is skipped rather than reassessed.
TERMINAL_STATUSES = {
    RecoveryCaseStatus.RECOVERED,
    RecoveryCaseStatus.PARTIALLY_RECOVERED,
    RecoveryCaseStatus.FAILED,
    RecoveryCaseStatus.STOPPED,
    RecoveryCaseStatus.ESCALATED,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/recovery-policy")
def get_recovery_policy():
    """
    The live guardrails.

    Served from the policy module's own constants so the interface cannot
    display limits that differ from the ones actually enforced.
    """
    return {
        "max_retries": MAX_RETRIES,
        "recovery_window_days": RECOVERY_WINDOW_DAYS,
        "high_risk_threshold": HIGH_RISK_THRESHOLD,
        "high_value_threshold": float(HIGH_VALUE_THRESHOLD),
        "stop_on_success": True,
        "duplicate_actions_blocked": True,
        "mode": "test_simulation",
    }


@router.post("/recovery-cases/{case_id}/run")
def run_recovery_agent(case_id: str, db: Session = Depends(get_db)):
    """Run the full recovery workflow for one case."""
    try:
        result = RecoveryOrchestratorService(db).run(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return result.__dict__


@router.post("/recovery-batch/run")
def run_recovery_batch(
    limit: int = Query(default=3, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Run the agent over a bounded slice of the open cases.

    A full retry ladder costs roughly forty commits against a remote
    database, so processing every open case in a single request runs past
    the host's request timeout. The caller repeats this endpoint until
    cases_remaining reaches zero, which also gives the interface
    something to report progress against.
    """
    orchestrator = RecoveryOrchestratorService(db)
    case_repository = RecoveryCaseRepository(db)

    open_cases = [
        case
        for case in case_repository.list_all()
        if case.status not in TERMINAL_STATUSES
    ]

    selected = open_cases[:limit]

    for case in selected:
        orchestrator.run(case.case_id)

    processed = len(selected)

    return {"cases_processed": processed, **_portfolio_metrics(db)}


@router.get("/recovery-metrics")
def get_recovery_metrics(db: Session = Depends(get_db)):
    """
    The portfolio figures without running anything.

    The same computation the batch returns, so the dashboard shows real
    numbers on load rather than staying blank until a batch has been run.
    """
    return _portfolio_metrics(db)


def _portfolio_metrics(db: Session) -> dict:
    # Every figure is read from the database rather than accumulated
    # while looping, so the totals reflect stored records and not a
    # counter an endpoint controls.
    case_repository = RecoveryCaseRepository(db)
    cases = case_repository.list_all()
    outcome_repository = RecoveryOutcomeRepository(db)
    recovered_totals = outcome_repository.get_recovered_totals()

    total_at_risk = sum(float(case.amount_at_risk) for case in cases)
    recovered = sum(float(value) for value in recovered_totals.values())

    def count(status):
        return sum(1 for case in cases if case.status == status)

    remaining_open = sum(
        1 for case in cases if case.status not in TERMINAL_STATUSES
    )

    # Three different figures, and conflating them is the usual way a
    # recovery dashboard overstates itself:
    #   at risk      — everything the agent is responsible for
    #   recoverable  — what it judges worth attempting, before acting
    #   recovered    — what actually came back, from the outcomes
    recoverable = _recoverable_revenue(db, cases)

    action_counts = RecoveryActionRepository(db).count_by_status()
    outcome_counts = outcome_repository.count_by_status()

    return {
        "cases_remaining": remaining_open,
        "total_cases_evaluated": len(cases),
        "total_revenue_at_risk": round(total_at_risk, 2),
        "recoverable_revenue": round(recoverable, 2),
        "revenue_recovered": round(recovered, 2),
        "remaining_revenue_at_risk": round(total_at_risk - recovered, 2),
        "recovery_rate": (
            round(recovered / total_at_risk * 100, 2) if total_at_risk else 0.0
        ),
        "recovery_attempts": sum(action_counts.values()),
        "actions_executed": (
            action_counts.get("completed", 0) + action_counts.get("failed", 0)
        ),
        "successful_recoveries": outcome_counts.get("recovered", 0),
        "partial_recoveries": outcome_counts.get("partially_recovered", 0),
        "failed_recoveries": outcome_counts.get("not_recovered", 0),
        "recovered_cases": count(RecoveryCaseStatus.RECOVERED),
        "failed_cases": count(RecoveryCaseStatus.FAILED),
        "escalated_cases": count(RecoveryCaseStatus.ESCALATED),
        "stopped_cases": count(RecoveryCaseStatus.STOPPED),
        "active_cases": remaining_open,
        "mode": "test_simulation",
    }


def _recoverable_revenue(db: Session, cases) -> float:
    """
    The revenue the policy authorised the agent to pursue.

    This is deliberately not "what came back". A case the policy cleared
    for action was judged recoverable whether or not the attempt
    succeeded, and the gap between this figure and the recovered one is
    how much the agent tried for and missed.

    A case the policy refused — high risk, high value, unrecoverable —
    is revenue at risk that was never recoverable by automation, and is
    excluded.
    """
    policy = RecoveryDecisionPolicy()
    risk_scores = RiskAssessmentRepository(db).get_latest_scores()
    attempted = RecoveryActionRepository(db).case_ids_with_actions()

    total = 0.0

    for case in cases:
        # Already acted on, so the policy authorised it at the time.
        if case.case_id in attempted:
            total += float(case.amount_at_risk)
            continue

        if case.status in TERMINAL_STATUSES:
            continue

        scores = risk_scores.get(case.case_id)

        # Not yet assessed, so there is no basis for calling it
        # recoverable. It stays counted as at risk only.
        if scores is None:
            continue

        decision = policy.authorize(
            recommended_action="retry_payment",
            risk_score=scores["risk"],
            recoverability_score=scores["recoverability"],
            amount_at_risk=case.amount_at_risk,
            retry_count=0,
            payment_already_recovered=False,
        )

        if decision.authorized:
            total += float(case.amount_at_risk)

    return total
