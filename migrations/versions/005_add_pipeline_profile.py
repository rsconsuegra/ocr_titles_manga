"""add pipeline_profiles table

Revision ID: 005
Revises: 004
Create Date: 2025-01-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    )
    op.create_index(
        "ix_pipeline_profiles_is_default", "pipeline_profiles", ["is_default"]
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_profiles_is_default", table_name="pipeline_profiles")
    op.drop_table("pipeline_profiles")
