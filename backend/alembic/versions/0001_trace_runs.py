"""trace_runs — the persisted trace lifecycle.

Revision ID: 0001
Revises:
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trace_runs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=True),
        sa.Column("start_address", sa.String(length=128), nullable=False),
        sa.Column("chain", sa.String(length=16), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("investigation", sa.JSON(), nullable=True),
        sa.Column("result_hash", sa.String(length=128), nullable=True),
        sa.Column("error", sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trace_runs")),
    )
    op.create_index(op.f("ix_trace_runs_case_id"), "trace_runs", ["case_id"])
    op.create_index(op.f("ix_trace_runs_status"), "trace_runs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_trace_runs_status"), table_name="trace_runs")
    op.drop_index(op.f("ix_trace_runs_case_id"), table_name="trace_runs")
    op.drop_table("trace_runs")
