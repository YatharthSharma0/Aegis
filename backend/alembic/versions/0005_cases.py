"""cases + complaints.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("ref_no", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("typology_hint", sa.String(length=48), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cases")),
        sa.UniqueConstraint("ref_no", name=op.f("uq_cases_ref_no")),
    )
    op.create_index(op.f("ix_cases_created_by"), "cases", ["created_by"])
    op.create_index(op.f("ix_cases_status"), "cases", ["status"])

    op.create_table(
        "complaints",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("case_id", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("raw_text", sa.String(length=8000), nullable=False),
        sa.Column("is_demo", sa.Boolean(), nullable=False),
        sa.Column("extracted", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_complaints")),
    )
    op.create_index(op.f("ix_complaints_case_id"), "complaints", ["case_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_complaints_case_id"), table_name="complaints")
    op.drop_table("complaints")
    op.drop_index(op.f("ix_cases_status"), table_name="cases")
    op.drop_index(op.f("ix_cases_created_by"), table_name="cases")
    op.drop_table("cases")
