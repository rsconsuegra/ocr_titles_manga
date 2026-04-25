# US-2B1: Sync Prompts with Agenta.ai

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: Step 1 (`agenta` dep), US-1A3 (PromptVersion table), Step 7 (migration 006)
**Blocks**: US-2B2 (create/edit pushes to Agenta), US-2B5 (browse with sync button)

---

## Overview

Create the `AgentaClient` module that provides bidirectional prompt sync between the local database and Agenta.ai. Agenta is the source of truth — when conflicts arise, Agenta wins. The client must handle offline/unreachable scenarios gracefully and provide a sync summary. Add Agenta settings to `settings.py` and a new DB migration for sync tracking columns.

---

## Implementation Details

### 1. `ocr_manga_title/settings.py` (additions)

```python
AGENTA_API_KEY = os.environ.get("AGENTA_API_KEY", "")
AGENTA_BASE_URL = os.environ.get("AGENTA_BASE_URL", "https://api.agenta.ai")
AGENTA_APP_ID = os.environ.get("AGENTA_APP_ID", "")
AGENTA_SYNC_ON_STARTUP = (
    os.environ.get("AGENTA_SYNC_ON_STARTUP", "false").lower() == "true"
)
```

### 2. `migrations/versions/006_add_prompt_sync_fields.py`

```python
"""Add source and last_synced_at columns to prompt_versions."""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    op.add_column(
        "prompt_versions",
        sa.Column("source", sa.String(), nullable=True, server_default="local"),
    )
    op.add_column(
        "prompt_versions",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prompt_versions", "last_synced_at")
    op.drop_column("prompt_versions", "source")
```

### 3. `ocr_manga_title/db/models.py` (PromptVersion update)

```python
class PromptVersion(Base):
    # ... existing columns ...
    source: Mapped[str | None] = mapped_column(default="local")
    last_synced_at: Mapped[datetime | None]
```

### 4. `ocr_manga_title/agenta_client.py`

```python
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.db.models import PromptVersion

logger = logging.getLogger(__name__)


class AgentaClient:
    def __init__(self, api_key: str, base_url: str, app_id: str):
        self._api_key = api_key
        self._base_url = base_url
        self._app_id = app_id

    def is_configured(self) -> bool:
        return bool(self._api_key and self._base_url and self._app_id)

    async def pull_prompts(
        self, session: AsyncSession
    ) -> list[PromptVersion]:
        """Fetch all prompts from Agenta, upsert into prompt_versions."""
        if not self.is_configured():
            return []

        import agenta

        agenta.init(api_key=self._api_key, base_url=self._base_url)
        remote_prompts = await self._fetch_remote_prompts()
        synced = []

        for remote in remote_prompts:
            existing = await self._find_by_agenta_id(session, remote.id)
            if existing:
                if self._remote_is_newer(remote, existing):
                    existing.content = remote.content
                    existing.last_synced_at = datetime.now(timezone.utc)
                    synced.append(existing)
            else:
                new_version = PromptVersion(
                    prompt_type="llm",
                    content=remote.content,
                    version_number=await self._next_version(session, "llm"),
                    agenta_id=remote.id,
                    is_active=False,
                    source="agenta",
                    last_synced_at=datetime.now(timezone.utc),
                )
                session.add(new_version)
                synced.append(new_version)

        await session.flush()
        return synced

    async def push_prompt(
        self, session: AsyncSession, prompt_version_id
    ) -> PromptVersion | None:
        """Push a local prompt version to Agenta."""
        if not self.is_configured():
            return None
        # Implementation: create or update in Agenta, store returned agenta_id
        ...

    async def sync(self, session: AsyncSession) -> dict:
        """Bidirectional sync: pull then push."""
        pulled = await self.pull_prompts(session)
        local_only = await self._get_local_only(session)
        pushed = []
        errors = []
        for pv in local_only:
            try:
                result = await self.push_prompt(session, pv.id)
                if result:
                    pushed.append(result)
            except Exception as e:
                errors.append(str(e))

        return {
            "pulled": len(pulled),
            "pushed": len(pushed),
            "conflicts": 0,
            "errors": errors,
        }

    async def _fetch_remote_prompts(self): ...
    async def _find_by_agenta_id(self, session, agenta_id): ...
    async def _get_local_only(self, session): ...
    async def _next_version(self, session, prompt_type): ...
    def _remote_is_newer(self, remote, local) -> bool: ...
```

### 5. `.env.example` (additions)

```
# Agenta.ai (optional — leave empty to disable sync)
AGENTA_API_KEY=
AGENTA_BASE_URL=https://api.agenta.ai
AGENTA_APP_ID=
AGENTA_SYNC_ON_STARTUP=false
```

---

## Acceptance Criteria

- [ ] `POST /api/v1/prompts/sync` triggers bidirectional sync
- [ ] Pull: fetches all prompts from Agenta, creates or updates `prompt_versions` rows
- [ ] Push: sends local-only versions (no `agenta_id`) to Agenta, stores returned ID
- [ ] Conflict resolution: Agenta version wins if timestamps differ
- [ ] Sync returns `{pulled: N, pushed: N, conflicts: N, errors: [...]}`
- [ ] Returns 503 if Agenta not configured (missing API key/base URL/app ID)
- [ ] If Agenta unreachable, returns error details without crashing; local DB unchanged
- [ ] Optional: `AGENTA_SYNC_ON_STARTUP=true` triggers sync on API server startup

---

## Test Specifications

**File**: `tests/test_agenta/__init__.py`

Empty init.

**File**: `tests/test_agenta/test_client.py`

Tests:
- `test_pull_creates_new_versions_from_agenta` — mock Agenta API to return 2 prompts; verify 2 new `PromptVersion` rows created with `source="agenta"`
- `test_pull_updates_existing_version` — mock Agenta API to return prompt matching existing `agenta_id` with newer content; verify content updated
- `test_push_creates_remote_prompt` — mock Agenta create API; verify `agenta_id` populated on local row
- `test_push_updates_remote_prompt` — mock Agenta update API for existing `agenta_id`; verify content pushed
- `test_sync_pulls_then_pushes` — mock both pull and push; verify sync returns correct counts
- `test_offline_fallback_returns_gracefully` — mock Agenta API to raise connection error; verify sync returns errors list, no crash
- `test_conflict_resolution_agenta_wins` — create local version with old timestamp, remote with new; verify local updated
- `test_not_configured_returns_early` — empty credentials; `is_configured()` returns `False`, pull/push return empty
- `test_is_configured_true_when_all_set` — all 3 credentials set; returns `True`
