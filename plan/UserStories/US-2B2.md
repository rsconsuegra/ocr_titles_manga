# US-2B2: Prompt CRUD API

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: US-1A3 (PromptVersion table), US-2B1 (AgentaClient)
**Blocks**: US-2B4 (frontend prompt list), US-2B5 (frontend prompt editor)

---

## Overview

Create full REST API for prompt version management. Endpoints cover CRUD operations, version activation, and diff comparison. The API integrates with AgentaClient to optionally push new/updated prompts to Agenta.ai.

---

## Implementation Details

### 1. `ocr_manga_title/api/schemas/prompts.py`

```python
from datetime import datetime

from pydantic import BaseModel


class PromptVersionResponse(BaseModel):
    id: int
    prompt_type: str
    content: str
    version_number: int
    agenta_id: str | None
    is_active: bool
    tags: list[str]
    source: str | None
    last_synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromptVersionCreateRequest(BaseModel):
    prompt_type: str
    content: str
    tags: list[str] = []
    activate: bool = False
    push_to_agenta: bool = False


class PromptVersionUpdateRequest(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class PromptDiffResponse(BaseModel):
    version_a: PromptVersionResponse
    version_b: PromptVersionResponse
    diff_lines: list[str]


class PromptSyncResponse(BaseModel):
    pulled: int
    pushed: int
    conflicts: int
    errors: list[str]
```

### 2. `ocr_manga_title/db/crud.py` (additions)

```python
async def create_prompt_version(
    session: AsyncSession,
    *,
    prompt_type: str,
    content: str,
    tags: list[str] | None = None,
    activate: bool = False,
) -> PromptVersion:
    count_q = await session.execute(
        select(func.count()).where(PromptVersion.prompt_type == prompt_type)
    )
    next_version = (count_q.scalar() or 0) + 1

    pv = PromptVersion(
        prompt_type=prompt_type,
        content=content,
        version_number=next_version,
        tags=tags or [],
        is_active=activate,
        source="local",
    )
    if activate:
        await session.execute(
            update(PromptVersion)
            .where(PromptVersion.prompt_type == prompt_type)
            .values(is_active=False)
        )
    session.add(pv)
    await session.flush()
    return pv


async def update_prompt_version(
    session: AsyncSession, version_id: int, **kwargs
) -> PromptVersion | None:
    pv = await session.get(PromptVersion, version_id)
    if not pv:
        return None
    for key, value in kwargs.items():
        setattr(pv, key, value)
    await session.flush()
    return pv


async def activate_prompt_version(
    session: AsyncSession, version_id: int
) -> PromptVersion | None:
    pv = await session.get(PromptVersion, version_id)
    if not pv:
        return None
    await session.execute(
        update(PromptVersion)
        .where(PromptVersion.prompt_type == pv.prompt_type)
        .values(is_active=False)
    )
    pv.is_active = True
    await session.flush()
    return pv


async def delete_prompt_version(
    session: AsyncSession, version_id: int
) -> bool:
    pv = await session.get(PromptVersion, version_id)
    if not pv:
        return False
    await session.delete(pv)
    await session.flush()
    return True


async def diff_prompt_versions(
    session: AsyncSession, id_a: int, id_b: int
) -> tuple[PromptVersion, PromptVersion] | None:
    a = await session.get(PromptVersion, id_a)
    b = await session.get(PromptVersion, id_b)
    if not a or not b:
        return None
    return (a, b)
```

### 3. `ocr_manga_title/api/routes/prompts.py`

```python
import difflib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.deps import get_session
from ocr_manga_title.api.schemas.prompts import (
    PromptVersionCreateRequest,
    PromptVersionResponse,
    PromptVersionUpdateRequest,
    PromptDiffResponse,
    PromptSyncResponse,
)
from ocr_manga_title.db import crud
from ocr_manga_title.db.models import PromptVersion
from ocr_manga_title.agenta_client import AgentaClient
from ocr_manga_title.settings import (
    AGENTA_API_KEY,
    AGENTA_BASE_URL,
    AGENTA_APP_ID,
)

router = APIRouter()


def _pv_to_response(pv: PromptVersion) -> PromptVersionResponse:
    return PromptVersionResponse.model_validate(pv)


@router.get("", response_model=list[PromptVersionResponse])
async def list_prompt_versions(
    prompt_type: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    rows = await crud.list_prompts(session, prompt_type=prompt_type)
    return [_pv_to_response(r) for r in rows]


@router.get("/{version_id}", response_model=PromptVersionResponse)
async def get_prompt_version(
    version_id: int,
    session: AsyncSession = Depends(get_session),
):
    pv = await session.get(PromptVersion, version_id)
    if not pv:
        raise HTTPException(404, "Prompt version not found")
    return _pv_to_response(pv)


@router.post("", response_model=PromptVersionResponse, status_code=201)
async def create_prompt_version(
    body: PromptVersionCreateRequest,
    session: AsyncSession = Depends(get_session),
):
    pv = await crud.create_prompt_version(
        session,
        prompt_type=body.prompt_type,
        content=body.content,
        tags=body.tags,
        activate=body.activate,
    )
    if body.push_to_agenta:
        client = AgentaClient(AGENTA_API_KEY, AGENTA_BASE_URL, AGENTA_APP_ID)
        if client.is_configured():
            await client.push_prompt(session, pv.id)
    return _pv_to_response(pv)


@router.patch("/{version_id}", response_model=PromptVersionResponse)
async def update_prompt_version_api(
    version_id: int,
    body: PromptVersionUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    updates = body.model_dump(exclude_unset=True)
    pv = await crud.update_prompt_version(session, version_id, **updates)
    if not pv:
        raise HTTPException(404, "Prompt version not found")
    return _pv_to_response(pv)


@router.post("/{version_id}/activate", response_model=PromptVersionResponse)
async def activate_prompt(
    version_id: int,
    session: AsyncSession = Depends(get_session),
):
    pv = await crud.activate_prompt_version(session, version_id)
    if not pv:
        raise HTTPException(404, "Prompt version not found")
    return _pv_to_response(pv)


@router.delete("/{version_id}", status_code=204)
async def delete_prompt(
    version_id: int,
    session: AsyncSession = Depends(get_session),
):
    deleted = await crud.delete_prompt_version(session, version_id)
    if not deleted:
        raise HTTPException(404, "Prompt version not found")


@router.get("/diff/{id_a}/{id_b}", response_model=PromptDiffResponse)
async def diff_prompts(
    id_a: int,
    id_b: int,
    session: AsyncSession = Depends(get_session),
):
    result = await crud.diff_prompt_versions(session, id_a, id_b)
    if not result:
        raise HTTPException(404, "One or both versions not found")
    a, b = result
    diff_lines = list(
        difflib.unified_diff(
            a.content.splitlines(),
            b.content.splitlines(),
            fromfile=f"v{a.version_number}",
            tofile=f"v{b.version_number}",
            lineterm="",
        )
    )
    return PromptDiffResponse(
        version_a=_pv_to_response(a),
        version_b=_pv_to_response(b),
        diff_lines=diff_lines,
    )


@router.post("/sync", response_model=PromptSyncResponse)
async def sync_with_agenta(
    session: AsyncSession = Depends(get_session),
):
    client = AgentaClient(AGENTA_API_KEY, AGENTA_BASE_URL, AGENTA_APP_ID)
    if not client.is_configured():
        raise HTTPException(503, "Agenta not configured")
    result = await client.sync(session)
    return PromptSyncResponse(**result)
```

### 4. `ocr_manga_title/api/app.py` (addition)

Register the prompts router:

```python
from ocr_manga_title.api.routes import prompts
app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
```

---

## Acceptance Criteria

- [ ] `GET /api/v1/prompts` returns all prompt versions, optional `?prompt_type=` filter
- [ ] `GET /api/v1/prompts/:id` returns a single prompt version
- [ ] `POST /api/v1/prompts` creates a new version with auto-incremented version_number
- [ ] `POST /api/v1/prompts/:id/activate` deactivates others of same type, activates target
- [ ] `PATCH /api/v1/prompts/:id` updates content/tags/active status
- [ ] `DELETE /api/v1/prompts/:id` deletes a version (404 if not found)
- [ ] `GET /api/v1/prompts/diff/:a/:b` returns unified diff between two versions
- [ ] `POST /api/v1/prompts/sync` triggers Agenta bidirectional sync
- [ ] `POST /api/v1/prompts` with `push_to_agenta=true` pushes to Agenta after creation
- [ ] All endpoints return proper HTTP status codes (200, 201, 204, 404, 503)

---

## Test Specifications

**File**: `tests/test_api/test_prompts_routes.py`

Tests:
- `test_list_prompts_returns_all` — seed 3 prompt versions; GET returns 3
- `test_list_prompts_filters_by_type` — seed 2 types; GET `?prompt_type=llm` returns only llm
- `test_get_prompt_returns_version` — seed version; GET by ID returns correct version
- `test_get_prompt_404_for_missing` — GET non-existent ID returns 404
- `test_create_prompt_auto_increments_version` — POST 2 prompts of same type; verify version_numbers 1 and 2
- `test_create_prompt_with_activate_true` — POST with `activate=true`; verify only this one is active
- `test_activate_prompt_deactivates_others` — activate version 2; verify version 1 `is_active=False`
- `test_update_prompt_content` — PATCH with new content; verify updated
- `test_delete_prompt_removes_version` — DELETE; GET returns 404
- `test_diff_returns_unified_diff` — create 2 versions with different content; verify diff_lines populated
- `test_sync_returns_503_when_not_configured` — mock empty credentials; POST /sync returns 503
- `test_create_with_push_to_agenta` — mock AgentaClient.push_prompt; verify called
