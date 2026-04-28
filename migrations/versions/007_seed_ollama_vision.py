"""seed ollama_vision model config

Revision ID: 007
Revises: 006
Create Date: 2026-04-24

"""
from typing import Sequence, Union

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
