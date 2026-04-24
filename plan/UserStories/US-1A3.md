# US-1A3: Store Prompt Versions

**Sub-phase**: 1A — Database Layer
**Depends on**: US-1A1 (tables must exist)
**Blocks**: US-1C1 (worker loads active prompt from DB)

---

## Overview

Create Alembic seed migration that reads the existing `prompts/llm/extract_title_v1.md` file and inserts it as the first prompt version in the database. This establishes the prompt versioning system that future phases (Agenta.ai integration) will build on.

---

## Implementation Details

### 1. `migrations/versions/003_seed_prompts.py`

Alembic migration that reads the prompt file and inserts into `prompt_versions`:

```python
from pathlib import Path

def upgrade() -> None:
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "llm" / "extract_title_v1.md"
    prompt_content = prompt_path.read_text()

    op.bulk_insert(
        sa.table(
            "prompt_versions",
            sa.column("id", sa.String),
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
                "id": str(uuid.uuid4()),
                "prompt_type": "llm",
                "content": prompt_content,
                "version_number": 1,
                "agenta_id": None,
                "is_active": True,
                "tags": "extraction,v1,initial",
                "created_at": datetime.now(timezone.utc),
            },
        ],
    )

def downgrade() -> None:
    op.execute("DELETE FROM prompt_versions WHERE prompt_type = 'llm' AND version_number = 1")
```

**Important**: The prompt file already exists at `prompts/llm/extract_title_v1.md` (19 lines). The migration reads it at migration-time, not runtime. This means the file must exist when running migrations.

### 2. CRUD function in `ocr_manga_title/db/crud.py`

Add prompt-related CRUD functions (this ticket creates the full `crud.py` file):

```python
from sqlalchemy import select
from ocr_manga_title.db.models import (
    PipelineRun, OCRResult, PostProcessingResult,
    PromptVersion, CatalogEntry, ModelConfig
)

async def get_active_prompt(session: AsyncSession, prompt_type: str) -> PromptVersion | None:
    stmt = select(PromptVersion).where(
        PromptVersion.prompt_type == prompt_type,
        PromptVersion.is_active == True
    ).order_by(PromptVersion.version_number.desc()).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_prompts(session: AsyncSession, prompt_type: str | None = None) -> list[PromptVersion]:
    stmt = select(PromptVersion).order_by(PromptVersion.created_at.desc())
    if prompt_type:
        stmt = stmt.where(PromptVersion.prompt_type == prompt_type)
    result = await session.execute(stmt)
    return list(result.scalars().all())
```

---

## Acceptance Criteria

- [ ] `alembic upgrade head` inserts 1 row into `prompt_versions`
- [ ] Row has `prompt_type="llm"`, `version_number=1`, `is_active=True`
- [ ] Row `content` matches the contents of `prompts/llm/extract_title_v1.md` exactly
- [ ] `downgrade()` removes the seeded row
- [ ] `get_active_prompt(session, "llm")` returns the seeded prompt
- [ ] `get_active_prompt(session, "ocr")` returns None (no OCR prompts in V2)
- [ ] Migration fails gracefully if prompt file doesn't exist (with clear error message)

---

## Test Specifications

**File**: `tests/test_db/test_crud.py` (partial — prompt CRUD)

Tests:
- Insert a PromptVersion, fetch with `get_active_prompt(session, "llm")`, verify content matches
- Insert two versions (v1 active, v2 inactive), verify `get_active_prompt` returns v1
- Insert two versions (v1 inactive, v2 active), verify `get_active_prompt` returns v2
- `list_prompts(session)` returns all versions
- `list_prompts(session, prompt_type="llm")` filters by type
