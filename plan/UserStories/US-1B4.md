# US-1B4: Inspect Run Details

**Sub-phase**: 1B — FastAPI Application
**Depends on**: US-1B2 (pipeline routes, get_pipeline_run_detail CRUD)
**Blocks**: US-1D3 (frontend run detail page)

---

## Overview

Implement the run detail endpoint that returns a complete view of a pipeline run including all OCR results and post-processing results. The route scaffold is in US-1B2; this ticket validates the eager-loaded query and response shape.

---

## Implementation Details

### 1. `GET /api/v1/pipeline/runs/{run_id}` response shape

```json
{
  "id": "uuid",
  "input_image_path": "uploads/abc123.png",
  "status": "completed",
  "error_message": null,
  "created_at": "2026-04-21T10:00:00",
  "completed_at": "2026-04-21T10:00:05",
  "ocr_results": [
    {
      "id": "uuid",
      "model_name": "tesseract",
      "raw_text": "One Piece\nISBN 4-06-319310-6",
      "confidence": 0.85,
      "processing_time_ms": 1200,
      "error": null,
      "created_at": "2026-04-21T10:00:02",
      "post_processing_results": [
        {
          "id": "uuid",
          "title_en": "One Piece",
          "title_ja": null,
          "code": "4063193106",
          "confidence": 0.9,
          "processing_type": "llm+rules",
          "created_at": "2026-04-21T10:00:04"
        }
      ]
    }
  ]
}
```

### 2. Query optimization

The `get_pipeline_run_detail` CRUD function uses `selectinload` to eagerly load:
- `PipelineRun.ocr_results` -> all OCRResult rows
- `OCRResult.post_processing_results` -> all PostProcessingResult rows

This avoids N+1 queries. One query fetches the entire run tree.

### 3. Error states

- Run exists but no OCR results yet (status="pending" or "processing"): returns `ocr_results: []`
- Run failed: `error_message` populated, may have partial `ocr_results`
- Run not found: 404

---

## Acceptance Criteria

- [ ] `GET /api/v1/pipeline/runs/{run_id}` returns full run with nested OCR + post-processing results
- [ ] Returns 404 for nonexistent run_id
- [ ] Pending runs return empty `ocr_results` array
- [ ] Completed runs return all OCR results with their post-processing results
- [ ] Failed runs return partial results + error_message
- [ ] Single query (no N+1) via eager loading

---

## Test Specifications

**File**: `tests/test_api/test_pipeline.py` (extend)

Tests:
- Get detail of pending run (no OCR results): returns run with `ocr_results: []`
- Get detail of completed run with OCR + post-processing results: full nested response
- Get detail with multiple OCR results (multiple models): all included
- Get detail of failed run: error_message present, partial results
- Get detail with nonexistent UUID: returns 404
- Verify nested post_processing_results array per OCR result
