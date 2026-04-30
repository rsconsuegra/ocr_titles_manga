"""initial schema – consolidated from former migrations 001-012

Revision ID: 001
Revises:
Create Date: 2025-01-01

"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


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
        sa.Column("batch_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_pipeline_runs_status", "pipeline_runs", ["status"])
    op.create_index("ix_pipeline_runs_created_at", "pipeline_runs", ["created_at"])
    op.create_index("ix_pipeline_runs_batch_run_id", "pipeline_runs", ["batch_run_id"])
    op.create_foreign_key(
        "fk_pipeline_runs_batch_run_id",
        "pipeline_runs",
        "batch_runs",
        ["batch_run_id"],
        ["id"],
    )

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
        sa.Column("blocks", sa.JSON(), nullable=True),
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
        sa.Column("system_prompt_used", sa.Text, nullable=True),
        sa.Column("user_prompt_used", sa.Text, nullable=True),
        sa.Column("temperature_used", sa.Float, nullable=True),
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

    op.create_table(
        "pipeline_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("preprocess_steps", sa.JSON, nullable=True),
        sa.Column("ocr_models", sa.JSON, nullable=True),
        sa.Column("enable_llm", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime, nullable=True, server_default=sa.func.now()
        ),
        sa.Column(
            "llm_provider",
            sa.String(20),
            nullable=False,
            server_default="openrouter",
        ),
        sa.Column("llm_config", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_pipeline_profiles_is_default", "pipeline_profiles", ["is_default"]
    )

    op.create_table(
        "image_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("image_hash", sa.String(64), nullable=False),
        sa.Column("config_hash", sa.String(64), nullable=False),
        sa.Column("cache_type", sa.String(20), nullable=False),
        sa.Column("result_path", sa.String(500), nullable=True),
        sa.Column("result_data", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint(
            "image_hash", "config_hash", "cache_type", name="uq_image_cache_lookup"
        ),
    )
    op.create_index("ix_image_cache_expires_at", "image_cache", ["expires_at"])

    op.create_table(
        "api_credentials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_name", sa.String(50), unique=True, nullable=False),
        sa.Column("encrypted_api_key", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "llm" / "extract_title_v1.md"
    if prompt_path.exists():
        prompt_content = prompt_path.read_text()
        op.bulk_insert(
            sa.table(
                "prompt_versions",
                sa.column("id", postgresql.UUID(as_uuid=True)),
                sa.column("prompt_type", sa.String),
                sa.column("content", sa.String),
                sa.column("version_number", sa.Integer),
                sa.column("agenta_id", sa.String),
                sa.column("is_active", sa.Boolean),
                sa.column("tags", sa.String),
                sa.column("created_at", sa.DateTime),
            ),
            [
                {
                    "id": uuid.uuid4(),
                    "prompt_type": "llm",
                    "content": prompt_content,
                    "version_number": 1,
                    "agenta_id": None,
                    "is_active": True,
                    "tags": "extraction,v1,initial",
                    "created_at": datetime.utcnow(),
                },
            ],
        )


def downgrade() -> None:
    op.drop_table("api_credentials")
    op.drop_index("ix_image_cache_expires_at", table_name="image_cache")
    op.drop_table("image_cache")
    op.drop_index("ix_pipeline_profiles_is_default", table_name="pipeline_profiles")
    op.drop_table("pipeline_profiles")
    op.drop_table("model_configs")
    op.drop_index("ix_catalog_entries_status", table_name="catalog_entries")
    op.drop_index("ix_catalog_entries_code", table_name="catalog_entries")
    op.drop_table("catalog_entries")
    op.drop_table("post_processing_results")
    op.drop_index("ix_ocr_results_pipeline_run_id", table_name="ocr_results")
    op.drop_table("ocr_results")
    op.drop_table("prompt_versions")
    op.drop_constraint(
        "fk_pipeline_runs_batch_run_id", "pipeline_runs", type_="foreignkey"
    )
    op.drop_index("ix_pipeline_runs_batch_run_id", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_created_at", table_name="pipeline_runs")
    op.drop_index("ix_pipeline_runs_status", table_name="pipeline_runs")
    op.drop_table("pipeline_runs")
    op.drop_index("ix_batch_runs_status", table_name="batch_runs")
    op.drop_table("batch_runs")
