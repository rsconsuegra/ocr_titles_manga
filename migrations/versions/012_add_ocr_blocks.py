"""add blocks column to ocr_results

Revision ID: 012
Revises: 011
Create Date: 2026-04-29

Stores OCR bounding-box / text-block data alongside raw OCR results so that
the RunDetail page can render bbox overlays on the original image.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "ocr_results",
        sa.Column("blocks", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ocr_results", "blocks")
