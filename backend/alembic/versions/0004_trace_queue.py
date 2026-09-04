"""trace_runs durable-queue columns: attempts, worker_id, lease_expires_at.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("trace_runs") as batch:
        batch.add_column(
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("worker_id", sa.String(length=64), nullable=True))
        batch.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("trace_runs") as batch:
        batch.drop_column("lease_expires_at")
        batch.drop_column("worker_id")
        batch.drop_column("attempts")
