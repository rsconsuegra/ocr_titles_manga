"""add llm_provider to pipeline_profiles

Revision ID: 008
Revises: 007
Create Date: 2026-04-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipeline_profiles",
        sa.Column(
            "llm_provider",
            sa.String(20),
            nullable=False,
            server_default="openrouter",
        ),
    )


def downgrade() -> None:
    op.drop_column("pipeline_profiles", "llm_provider")
