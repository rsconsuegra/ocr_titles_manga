"""seed prompt versions

Revision ID: 003
Revises: 002
Create Date: 2025-01-01

"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "llm" / "extract_title_v1.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
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
    op.execute("DELETE FROM prompt_versions WHERE prompt_type = 'llm' AND version_number = 1")
