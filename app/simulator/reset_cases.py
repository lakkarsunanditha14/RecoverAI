"""
Reset recovery cases back to a clean demo state.

Run with:

    python -m app.simulator.reset_cases

Keeps the newest case still in "created" status for each payment and
deletes everything else, along with the rows that reference it.

The test suite runs against the same database as the demo, so every
pytest run leaves extra cases behind. Run this afterwards to get the
dashboard back to one case per payment.
"""

from sqlalchemy import text

from app.core.database import SessionLocal
from app.services.recovery_case_service import RecoveryCaseService


# Children first: the foreign keys to recovery_cases are NO ACTION, so
# nothing can be removed before the rows pointing at it are gone.
# recovery_outcomes also references recovery_actions, so it leads.
CHILD_TABLES = [
    "recovery_outcomes",
    "audit_events",
    "recovery_actions",
    "recovery_decisions",
    "risk_assessments",
]


def reset() -> tuple[int, int, int]:
    db = SessionLocal()

    try:
        # Prefer a case still in "created" status so the workflow can be
        # demonstrated from the start, but fall back to the newest case of
        # any status: dropping a payment off the dashboard entirely is
        # worse than keeping an already-completed case.
        keep = [
            row[0]
            for row in db.execute(
                text(
                    """
                    select distinct on (payment_id) case_id
                    from recovery_cases
                    order by
                        payment_id,
                        (status = 'created') desc,
                        created_at desc
                    """
                )
            )
        ]

        deleted = 0

        for table in CHILD_TABLES + ["recovery_cases"]:
            deleted += db.execute(
                text(f"delete from {table} where case_id != all(:keep)"),
                {"keep": keep},
            ).rowcount

        # A payment whose cases were all deleted would vanish from the
        # dashboard, and the workflow can only start from a case.
        missing = [
            row[0]
            for row in db.execute(
                text(
                    """
                    select payment_id from payments
                    where payment_id not in (
                        select payment_id from recovery_cases
                    )
                    """
                )
            )
        ]

        service = RecoveryCaseService(db)

        for payment_id in missing:
            service.create_case(payment_id)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return len(keep), deleted, len(missing)


if __name__ == "__main__":
    kept, deleted, restored = reset()
    print(
        f"Kept {kept} recovery cases, deleted {deleted} rows, "
        f"restored {restored} missing."
    )
