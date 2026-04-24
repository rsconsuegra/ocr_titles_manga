# US-1B5: Browse Extraction Results

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1B1 (API structure, schemas)
**Blocks**: US-1D3 (frontend override form)

---

## Overview

Create the results endpoint for listing post-processing results with filters, and the override endpoint for manual corrections. This lets operators review extraction quality and fix mistakes.

---

## Implementation Details

### 1. `ocr_manga_title/api/routes/results.py`

```python
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas import (
    PostProcessingResultResponse, PaginatedResponse, ResultOverrideRequest
)
from ocr_manga_title.db.models import PostProcessingResult, OCRResult, CatalogEntry

router = APIRouter()

@router.get("", response_model=PaginatedResponse)
async def list_results(
    model_name: str | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PostProcessingResult).join(OCRResult).order_by(PostProcessingResult.created_at.desc())
    count_stmt = select(sa_func.count()).select_from(PostProcessingResult).join(OCRResult)

    if model_name:
        stmt = stmt.where(OCRResult.model_name == model_name)
        count_stmt = count_stmt.where(OCRResult.model_name == model_name)
    if min_confidence is not None:
        stmt = stmt.where(PostProcessingResult.confidence >= min_confidence)
        count_stmt = count_stmt.where(PostProcessingResult.confidence >= min_confidence)
    if max_confidence is not None:
        stmt = stmt.where(PostProcessingResult.confidence <= max_confidence)
        count_stmt = count_stmt.where(PostProcessingResult.confidence <= max_confidence)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = [PostProcessingResultResponse.model_validate(r) for r in result.scalars().all()]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

@router.put("/{result_id}/override", response_model=PostProcessingResultResponse)
async def override_result(
    result_id: uuid.UUID,
    body: ResultOverrideRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PostProcessingResult).where(PostProcessingResult.id == result_id)
    result = await db.execute(stmt)
    pp_result = result.scalar_one_or_none()
    if not pp_result:
        raise HTTPException(status_code=404, detail="Post-processing result not found")

    if body.title_en is not None:
        pp_result.title_en = body.title_en
    if body.title_ja is not None:
        pp_result.title_ja = body.title_ja
    if body.code is not None:
        pp_result.code = body.code

    await db.flush()

    # Update linked catalog entry if exists
    from ocr_manga_title.db.crud import get_catalog_entry_by_run
    catalog = await get_catalog_entry_by_run(db, pp_result.ocr_result.pipeline_run_id)
    if catalog:
        if body.title_en is not None:
            catalog.title_en = body.title_en
        if body.title_ja is not None:
            catalog.title_ja = body.title_ja
        if body.code is not None:
            catalog.code = body.code
        catalog.status = "needs_review"
        await db.flush()

    await db.refresh(pp_result)
    return PostProcessingResultResponse.model_validate(pp_result)
```

### 2. CRUD addition for catalog lookup

```python
async def get_catalog_entry_by_run(session: AsyncSession, run_id: uuid.UUID) -> CatalogEntry | None:
    stmt = select(CatalogEntry).where(CatalogEntry.source_run_id == run_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

---

## Acceptance Criteria

- [ ] `GET /api/v1/results` returns paginated list of post-processing results
- [ ] `?model_name=tesseract` filters by OCR model
- [ ] `?min_confidence=0.5` filters by minimum confidence
- [ ] `?max_confidence=0.9` filters by maximum confidence
- [ ] Combined filters work together
- [ ] `PUT /api/v1/results/{result_id}/override` updates title_en, title_ja, code
- [ ] Override propagates to linked catalog entry (if exists)
- [ ] Catalog entry status reset to "needs_review" after override
- [ ] Returns 404 for nonexistent result_id
- [ ] Empty results returns `{"items": [], "total": 0}`

---

## Test Specifications

**File**: `tests/test_api/test_results.py`

Tests:
- List results on empty DB: returns empty paginated response
- Insert 3 results via DB, list all: returns 3 items
- Filter by model_name: only matching results
- Filter by min_confidence=0.7: only results >= 0.7
- Filter by confidence range (0.5-0.9): only results in range
- Override result title_en: returns updated response
- Override result code: returns updated response
- Override propagates to catalog entry
- Override nonexistent result: returns 404
