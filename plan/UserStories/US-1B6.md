# US-1B6: Manage Catalog Entries

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1B1 (API structure, schemas, CRUD)
**Blocks**: US-1D4 (frontend catalog page)

---

## Overview

Create catalog CRUD endpoints: list (with search and filter), get single entry, update entry status/fields, and CSV export. The catalog is the curated list of extracted manga titles that operators review and manage.

---

## Implementation Details

### 1. `ocr_manga_title/api/routes/catalog.py`

```python
import csv
import io
import uuid
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func as sa_func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas import CatalogEntryResponse, PaginatedResponse, CatalogUpdateRequest
from ocr_manga_title.db.models import CatalogEntry
from ocr_manga_title.db.crud import (
    get_catalog_entry, list_catalog_entries,
    update_catalog_entry, count_catalog_entries
)

router = APIRouter()

@router.get("", response_model=PaginatedResponse)
async def list_catalog(
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CatalogEntry).order_by(CatalogEntry.created_at.desc())
    count_stmt = select(sa_func.count()).select_from(CatalogEntry)

    if status:
        stmt = stmt.where(CatalogEntry.status == status)
        count_stmt = count_stmt.where(CatalogEntry.status == status)

    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            CatalogEntry.title_en.ilike(search_pattern),
            CatalogEntry.title_ja.ilike(search_pattern),
            CatalogEntry.code.ilike(search_pattern),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = [CatalogEntryResponse.model_validate(e) for e in result.scalars().all()]

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)

@router.get("/export")
async def export_catalog(db: AsyncSession = Depends(get_db)):
    stmt = select(CatalogEntry).order_by(CatalogEntry.created_at.desc())
    result = await db.execute(stmt)
    entries = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "title_en", "title_ja", "code", "status", "confidence", "source_run_id", "created_at", "updated_at"])
    for entry in entries:
        writer.writerow([
            entry.id, entry.title_en, entry.title_ja, entry.code,
            entry.status, entry.confidence, entry.source_run_id,
            entry.created_at.isoformat() if entry.created_at else "",
            entry.updated_at.isoformat() if entry.updated_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=catalog_export.csv"},
    )

@router.get("/{entry_id}", response_model=CatalogEntryResponse)
async def get_catalog(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    entry = await get_catalog_entry(session=db, entry_id=entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return CatalogEntryResponse.model_validate(entry)

@router.put("/{entry_id}", response_model=CatalogEntryResponse)
async def update_catalog(
    entry_id: uuid.UUID,
    body: CatalogUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    entry = await get_catalog_entry(session=db, entry_id=entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog entry not found")

    updates = {}
    if body.status is not None:
        if body.status not in ("auto_confirmed", "needs_review", "rejected"):
            raise HTTPException(status_code=400, detail="Invalid status. Must be: auto_confirmed, needs_review, rejected")
        updates["status"] = body.status
    if body.title_en is not None:
        updates["title_en"] = body.title_en
    if body.title_ja is not None:
        updates["title_ja"] = body.title_ja
    if body.code is not None:
        updates["code"] = body.code

    if updates:
        updates["updated_at"] = datetime.now(timezone.utc)
        updated = await update_catalog_entry(session=db, entry_id=entry_id, **updates)
        return CatalogEntryResponse.model_validate(updated)
    return CatalogEntryResponse.model_validate(entry)
```

**Route ordering note**: `/export` must be defined BEFORE `/{entry_id}` to avoid FastAPI treating "export" as a UUID path param.

### 2. CRUD functions (already in crud.py from US-1A3, verify these exist)

```python
async def get_catalog_entry(session: AsyncSession, entry_id: uuid.UUID) -> CatalogEntry | None:
    stmt = select(CatalogEntry).where(CatalogEntry.id == entry_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

async def list_catalog_entries(session, status=None, search=None, limit=20, offset=0) -> list[CatalogEntry]:
    # Used internally; API route builds its own query for pagination
    ...

async def update_catalog_entry(session: AsyncSession, entry_id: uuid.UUID, **kwargs) -> CatalogEntry | None:
    entry = await get_catalog_entry(session, entry_id)
    if not entry:
        return None
    for key, value in kwargs.items():
        if hasattr(entry, key):
            setattr(entry, key, value)
    await session.flush()
    await session.refresh(entry)
    return entry

async def count_catalog_entries(session: AsyncSession, status: str | None = None) -> int:
    stmt = select(sa_func.count()).select_from(CatalogEntry)
    if status:
        stmt = stmt.where(CatalogEntry.status == status)
    result = await session.execute(stmt)
    return result.scalar_one()
```

---

## Acceptance Criteria

- [ ] `GET /api/v1/catalog` returns paginated list of catalog entries
- [ ] `?status=needs_review` filters by status
- [ ] `?search=one+piece` searches title_en, title_ja, code (case-insensitive, partial match)
- [ ] `?search=978` finds entries by ISBN code
- [ ] `GET /api/v1/catalog/{entry_id}` returns single entry
- [ ] Returns 404 for nonexistent entry_id
- [ ] `PUT /api/v1/catalog/{entry_id}` updates status, title_en, title_ja, code
- [ ] Status validation: only accepts auto_confirmed, needs_review, rejected
- [ ] `updated_at` set automatically on update
- [ ] `GET /api/v1/catalog/export` returns CSV download
- [ ] CSV has correct columns and all rows
- [ ] Empty catalog returns empty items, CSV with headers only

---

## Test Specifications

**File**: `tests/test_api/test_catalog.py`

Tests:
- Empty catalog: returns `{"items": [], "total": 0}`
- Insert 3 entries, list all: returns 3 items
- Filter by status=needs_review: only matching
- Search by title_en: partial match, case-insensitive
- Search by code: ISBN match
- Search with no results: returns empty
- Get single entry by ID: correct response
- Get nonexistent entry: 404
- Update entry status: returns updated entry
- Update entry title_en + code: returns updated entry
- Update with invalid status: returns 400
- Update nonexistent entry: 404
- Export CSV: returns text/csv with correct headers and rows
- Export empty catalog: CSV with headers only
