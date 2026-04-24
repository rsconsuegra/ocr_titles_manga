"""add batch_run table and FK

Revision ID: 004
Revises: 003
Create Date: 2025-01-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batch_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("total_count", sa.Integer, nullable=False),
        sa.Column("completed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_batch_runs_status", "batch_runs", ["status"])

    op.add_column(
        "pipeline_runs",
        sa.Column("batch_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_pipeline_runs_batch_run_id", "pipeline_runs", ["batch_run_id"]
    )
    op.create_foreign_key(
        "fk_pipeline_runs_batch_run_id",
        "pipeline_runs",
        "batch_runs",
        ["batch_run_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_pipeline_runs_batch_run_id", "pipeline_runs", type_="foreignkey"
    )
    op.drop_index("ix_pipeline_runs_batch_run_id", table_name="pipeline_runs")
    op.drop_column("pipeline_runs", "batch_run_id")
    op.drop_index("ix_batch_runs_status", table_name="batch_runs")
    op.drop_table("batch_runs")
