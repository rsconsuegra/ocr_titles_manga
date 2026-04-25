"""add image_cache table

Revision ID: 006
Revises: 005
Create Date: 2026-04-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_index("ix_image_cache_expires_at", table_name="image_cache")
    op.drop_table("image_cache")
