"""remove auto-seeded model config rows

Revision ID: 011
Revises: 010
Create Date: 2026-04-28

Model config is now sourced from config/ocrs.yaml with DB rows used only
for user overrides.  Remove the rows that were auto-seeded by migrations
002 and 007 so that the YAML file becomes the effective source of truth.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

_SEEDED_MODELS = ("tesseract", "paddle", "easyocr", "glm_ocr", "ollama_vision")


def upgrade() -> None:
    placeholders = ", ".join(f":m{i}" for i in range(len(_SEEDED_MODELS)))
    op.execute(
        sa.text(
            f"DELETE FROM model_configs WHERE model_name IN ({placeholders})"
        ).bindparams(**{f"m{i}": name for i, name in enumerate(_SEEDED_MODELS)})
    )


def downgrade() -> None:
    pass
