"""Catalog CRUD endpoints - list, get, update, and export catalog entries."""

import csv
import io
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func as sa_func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.dependencies import get_db
from ocr_manga_title.api.schemas.catalog import (
    CatalogEntryResponse,
    CatalogUpdateRequest,
)
from ocr_manga_title.api.schemas.pipeline import PaginatedResponse
from ocr_manga_title.db.crud import get_catalog_entry, update_catalog_entry
from ocr_manga_title.db.enums import CatalogStatus
from ocr_manga_title.db.models import CatalogEntry
from ocr_manga_title.schemas import utcnow

router = APIRouter()


@router.get("", response_model=PaginatedResponse[CatalogEntryResponse])
async def list_catalog(
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaginatedResponse[CatalogEntryResponse]:
    """List catalog entries with optional filtering and pagination."""
    stmt = select(CatalogEntry).order_by(CatalogEntry.created_at.desc())
    count_stmt = select(sa_func.count()).select_from(CatalogEntry)

    if status:
        stmt = stmt.where(CatalogEntry.status == status)
        count_stmt = count_stmt.where(CatalogEntry.status == status)

    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{escaped}%"
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
async def export_catalog(db: AsyncSession = Depends(get_db)) -> StreamingResponse:
    """Export all catalog entries as a streaming CSV download."""
    chunk_size = 500

    def _csv_header() -> str:
        buf = io.StringIO()
        csv.writer(buf).writerow(
            [
                "id", "title_en", "title_ja", "code", "status",
                "confidence", "source_run_id", "created_at", "updated_at",
            ]
        )
        return buf.getvalue()

    def _csv_row(entry: Any) -> str:
        buf = io.StringIO()
        csv.writer(buf).writerow(
            [
                entry.id,
                entry.title_en,
                entry.title_ja,
                entry.code,
                entry.status,
                entry.confidence,
                entry.source_run_id,
                entry.created_at.isoformat() if entry.created_at else "",
                entry.updated_at.isoformat() if entry.updated_at else "",
            ]
        )
        return buf.getvalue()

    async def _generate() -> AsyncIterator[str]:
        yield _csv_header()
        offset = 0
        while True:
            stmt = (
                select(CatalogEntry)
                .order_by(CatalogEntry.created_at.desc())
                .offset(offset)
                .limit(chunk_size)
            )
            result = await db.execute(stmt)
            chunk = result.scalars().all()
            if not chunk:
                break
            for entry in chunk:
                yield _csv_row(entry)
            offset += chunk_size

    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=catalog_export.csv"},
    )


@router.get("/{entry_id}", response_model=CatalogEntryResponse)
async def get_single_catalog(entry_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> CatalogEntryResponse:
    """Retrieve a single catalog entry by ID."""
    entry = await get_catalog_entry(session=db, entry_id=entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found"
        )
    return CatalogEntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=CatalogEntryResponse)
async def update_catalog(
    entry_id: uuid.UUID,
    body: CatalogUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> CatalogEntryResponse:
    """Update fields on an existing catalog entry."""
    entry = await get_catalog_entry(session=db, entry_id=entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Catalog entry not found"
        )

    updates: dict[str, Any] = {}
    if body.status is not None:
        if body.status not in (s.value for s in CatalogStatus):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be: auto_confirmed, needs_review, rejected",
            )
        updates["status"] = body.status
    if body.title_en is not None:
        updates["title_en"] = body.title_en
    if body.title_ja is not None:
        updates["title_ja"] = body.title_ja
    if body.code is not None:
        updates["code"] = body.code

    if updates:
        updates["updated_at"] = utcnow()
        updated = await update_catalog_entry(session=db, entry_id=entry_id, **updates)
        return CatalogEntryResponse.model_validate(updated)
    return CatalogEntryResponse.model_validate(entry)
