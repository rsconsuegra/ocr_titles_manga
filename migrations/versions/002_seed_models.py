"""seed model configs

Revision ID: 002
Revises: 001
Create Date: 2025-01-01

"""
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "model_configs",
            sa.column("id", postgresql.UUID(as_uuid=True)),
            sa.column("model_name", sa.String),
            sa.column("is_enabled", sa.Boolean),
            sa.column("parameters", sa.JSON),
            sa.column("language_hint", sa.String),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "id": uuid.uuid4(),
                "model_name": "tesseract",
                "is_enabled": True,
                "parameters": {
                    "languages": ["eng", "jpn"],
                    "psm": 3,
                    "oem": 3,
                },
                "language_hint": "eng+jpn",
                "updated_at": datetime.utcnow(),
            },
            {
                "id": uuid.uuid4(),
                "model_name": "paddle",
                "is_enabled": False,
                "parameters": {"languages": ["en", "ja"], "use_gpu": False},
                "language_hint": "en+ja",
                "updated_at": datetime.utcnow(),
            },
            {
                "id": uuid.uuid4(),
                "model_name": "easyocr",
                "is_enabled": False,
                "parameters": {"languages": ["en", "ja"], "gpu": False},
                "language_hint": "en+ja",
                "updated_at": datetime.utcnow(),
            },
            {
                "id": uuid.uuid4(),
                "model_name": "glm_ocr",
                "is_enabled": False,
                "parameters": {
                    "api_endpoint": "",
                    "model": "google/gemini-2.5-flash",
                    "api_key": "",
                    "prompt": "Extract all text from this image.",
                },
                "language_hint": None,
                "updated_at": datetime.utcnow(),
            },
        ],
    )


def downgrade() -> None:
    op.execute("DELETE FROM model_configs WHERE model_name IN ('tesseract', 'paddle', 'easyocr', 'glm_ocr')")
