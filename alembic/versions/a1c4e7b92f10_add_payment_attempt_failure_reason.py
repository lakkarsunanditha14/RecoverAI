"""add payment attempt failure reason

Revision ID: a1c4e7b92f10
Revises: 76b3fe9d369a
Create Date: 2026-09-06

The recovery agent could score how badly a payment was doing but not why
it failed, so every case was diagnosed the same way. The reason the
provider gave is what separates an expired card from a temporary bank
timeout, and those two want different recovery strategies.

Nullable: attempts recorded before this column existed keep working and
are diagnosed from their status pattern instead.
"""

from alembic import op
import sqlalchemy as sa


revision = "a1c4e7b92f10"
down_revision = "76b3fe9d369a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_attempts",
        sa.Column("failure_reason", sa.String(length=60), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("payment_attempts", "failure_reason")
