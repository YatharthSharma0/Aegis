"""audit_log — hash-chained, append-only.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column(
            "seq",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(length=32), nullable=True),
        sa.Column("actor_role", sa.String(length=16), nullable=True),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("trace_id", sa.String(length=32), nullable=True),
        sa.Column("case_id", sa.String(length=64), nullable=True),
        sa.Column("address", sa.String(length=128), nullable=True),
        sa.Column("chain", sa.String(length=16), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("result_hash", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=32), nullable=True),
        sa.Column("prev_row_hash", sa.String(length=64), nullable=False),
        sa.Column("row_hash", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("seq", name=op.f("pk_audit_log")),
        sa.UniqueConstraint("row_hash", name=op.f("uq_audit_log_row_hash")),
    )
    op.create_index(op.f("ix_audit_log_action"), "audit_log", ["action"])
    op.create_index(op.f("ix_audit_log_actor_id"), "audit_log", ["actor_id"])
    op.create_index(op.f("ix_audit_log_trace_id"), "audit_log", ["trace_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_trace_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_action"), table_name="audit_log")
    op.drop_table("audit_log")
