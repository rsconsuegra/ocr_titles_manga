"""add llm_config to profiles and prompt audit to post_processing_results

Revision ID: 009
Revises: 008
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_profiles",
        sa.Column("llm_config", sa.JSON, nullable=True),
    )
    op.add_column(
        "post_processing_results",
        sa.Column("system_prompt_used", sa.Text, nullable=True),
    )
    op.add_column(
        "post_processing_results",
        sa.Column("user_prompt_used", sa.Text, nullable=True),
    )
    op.add_column(
        "post_processing_results",
        sa.Column("temperature_used", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("post_processing_results", "temperature_used")
    op.drop_column("post_processing_results", "user_prompt_used")
    op.drop_column("post_processing_results", "system_prompt_used")
    op.drop_column("pipeline_profiles", "llm_config")
