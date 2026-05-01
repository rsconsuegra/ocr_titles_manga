"""add extra_metadata to post_processing_results

Revision ID: 6e6dc63619af
Revises: df2ddc82063a
Create Date: 2026-04-30 20:01:36.792488

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6e6dc63619af'
down_revision: Union[str, None] = 'df2ddc82063a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('post_processing_results', sa.Column('extra_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('post_processing_results', 'extra_metadata')
