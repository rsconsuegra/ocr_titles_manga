"""add raw_response to post_processing_results

Revision ID: df2ddc82063a
Revises: 001
Create Date: 2026-04-30 17:12:21.036324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'df2ddc82063a'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('post_processing_results', sa.Column('raw_response', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('post_processing_results', 'raw_response')
