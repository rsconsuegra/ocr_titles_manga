# US-1B3: View Pipeline Run History

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1B2 (pipeline routes created)
**Blocks**: US-1D2 (frontend runs page)

---

## Overview

Implement the paginated run listing endpoint. The route structure is already created in US-1B2. This ticket ensures the listing, filtering, and pagination work correctly with real database queries.

---

## Implementation Details

The route `GET /api/v1/pipeline/runs` is already scaffolded in US-1B2. This ticket validates and completes:

### 1. CRUD function `list_pipeline_runs` (already in crud.py)

Verify the query:
- `select(PipelineRun).order_by(PipelineRun.created_at.desc())`
- Optional `.where(PipelineRun.status == status)` filter
- `.offset(offset).limit(limit)` pagination
- Returns `list[PipelineRun]`

### 2. CRUD function `count_pipeline_runs` (already in crud.py)

Verify:
- `select(func.count()).select_from(PipelineRun)`
- Optional status filter
- Returns `int`

### 3. Response format

```json
{
  "items": [
    {
      "id": "uuid",
      "input_image_path": "uploads/abc123.png",
      "status": "completed",
      "error_message": null,
      "created_at": "2026-04-21T10:00:00",
      "completed_at": "2026-04-21T10:00:05"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

## Acceptance Criteria

- [ ] `GET /api/v1/pipeline/runs` returns paginated list sorted by created_at desc
- [ ] Default pagination: limit=20, offset=0
- [ ] `?status=completed` filters to completed runs only
- [ ] `?status=pending` filters to pending runs only
- [ ] `?limit=5&offset=10` returns items 11-15
- [ ] `total` field reflects total count matching filters (not just page size)
- [ ] Empty database returns `{"items": [], "total": 0, "limit": 20, "offset": 0}`
- [ ] limit capped at 100, minimum 1
- [ ] offset minimum 0

---

## Test Specifications

**File**: `tests/test_api/test_pipeline.py` (extend)

Tests:
- Empty DB: returns `{"items": [], "total": 0}`
- Insert 5 runs, list all: returns 5 items, total=5
- Insert 5 runs (3 completed, 2 pending), filter status=completed: returns 3 items, total=3
- Insert 25 runs, limit=10, offset=0: returns 10 items, total=25
- Insert 25 runs, limit=10, offset=20: returns 5 items, total=25
- Sorted by created_at desc (newest first)
