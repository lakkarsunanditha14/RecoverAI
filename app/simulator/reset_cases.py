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


def reset() -> tuple[int, int]:
    db = SessionLocal()

    try:
        keep = [
            row[0]
            for row in db.execute(
                text(
                    """
                    select distinct on (payment_id) case_id
                    from recovery_cases
                    where status = 'created'
                    order by payment_id, created_at desc
                    """
                )
            )
        ]

        if not keep:
            raise RuntimeError(
                "No case in 'created' status to keep. Refusing to delete "
                "every recovery case: the frontend cannot create new ones."
            )

        deleted = 0

        for table in CHILD_TABLES + ["recovery_cases"]:
            deleted += db.execute(
                text(f"delete from {table} where case_id != all(:keep)"),
                {"keep": keep},
            ).rowcount

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return len(keep), deleted


if __name__ == "__main__":
    kept, deleted = reset()
    print(f"Kept {kept} recovery cases, deleted {deleted} rows.")
