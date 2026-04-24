"""initial tables

Revision ID: 001
Revises:
Create Date: 2025-01-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("input_image_path", sa.String(500), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=True),
        sa.Column("source_platform", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("preprocess_config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])
    op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])

    op.create_table(
        "prompt_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prompt_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("agenta_id", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("false")),
        sa.Column("tags", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "ocr_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("processing_time_ms", sa.Integer, nullable=False),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_ocr_results_pipeline_run_id", "ocr_results", ["pipeline_run_id"])

    op.create_table(
        "post_processing_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ocr_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ocr_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prompt_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prompt_versions.id"),
            nullable=True,
        ),
        sa.Column("title_en", sa.String(500), nullable=True),
        sa.Column("title_ja", sa.String(500), nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("processing_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "catalog_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title_en", sa.String(500), nullable=True),
        sa.Column("title_ja", sa.String(500), nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column(
            "source_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id"),
            nullable=False,
        ),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("status", sa.String(20), server_default="needs_review"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_catalog_entries_code", "catalog_entries", ["code"])
    op.create_index("ix_catalog_entries_status", "catalog_entries", ["status"])

    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_name", sa.String(50), unique=True, nullable=False),
        sa.Column("is_enabled", sa.Boolean, server_default=sa.text("true")),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("language_hint", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("model_configs")
    op.drop_table("catalog_entries")
    op.drop_table("post_processing_results")
    op.drop_table("ocr_results")
    op.drop_table("prompt_versions")
    op.drop_table("pipeline_runs")
