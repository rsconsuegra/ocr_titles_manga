# API Reference

## Overview

- **Base URL**: `http://localhost:8000`
- **API Prefix**: `/api/v1`
- **OpenAPI Docs**: `http://localhost:8000/api/docs` (Swagger UI)
- **OpenAPI Spec**: `http://localhost:8000/api/openapi.json`
- **Content-Type**: `application/json` (unless noted as `multipart/form-data`)

---

## Route Modules

| Router | Prefix | File | Endpoints |
|---|---|---|---|
| Inputs | `/api/v1/inputs` | `api/routes/pipeline/inputs.py` | 2 |
| Pipeline Runs | `/api/v1/pipeline` | `api/routes/pipeline/runs.py` + `run.py` | 6 |
| Results | `/api/v1/results` | `api/routes/pipeline/results.py` | 2 |
| Catalog | `/api/v1/catalog` | `api/routes/config/catalog.py` | 4 |
| Models | `/api/v1/models` | `api/routes/ocr/models.py` | 2 |
| Preprocess | `/api/v1/preprocess` | `api/routes/ocr/preprocess.py` | 4 |
| OCR | `/api/v1/ocr` | `api/routes/ocr/ocr.py` | 3 |
| Run | `/api/v1/run` | `api/routes/pipeline/run.py` | 1 |
| Batches | `/api/v1/batches` | `api/routes/pipeline/batches.py` | 4 |
| Profiles | `/api/v1/profiles` | `api/routes/config/profiles.py` | 9 |
| Ollama | `/api/v1/ollama` | `api/routes/config/ollama.py` | 3 |
| LLM | `/api/v1/llm` | `api/routes/config/llm.py` | 2 |
| Settings | `/api/v1/settings` | `api/routes/config/settings.py` | 7 |

**Total: 49 endpoints across 13 route modules**

---

## Inputs (`/api/v1/inputs`)

### `POST /upload`

Upload one or more images and create pipeline runs.

- **Content-Type**: `multipart/form-data`
- **Query Params**: `profile_id` (UUID, optional) — if set, snapshots the profile config into each run
- **Body**: `files` — up to 10 image files

**Response**: `list[PipelineRunResponse]`

```json
[
  {
    "id": "uuid",
    "input_image_path": "uploads/abc123.png",
    "status": "pending",
    "error_message": null,
    "created_at": "2026-01-15T10:00:00",
    "completed_at": null
  }
]
```

### `GET /{run_id}`

Retrieve a single pipeline run.

**Response**: `PipelineRunResponse`

---

## Pipeline (`/api/v1/pipeline`)

### `POST /run/{run_id}`

Enqueue a pending pipeline run for async processing via Dramatiq.

- **Status check**: Returns 409 if not `pending`

**Response**:
```json
{ "message": "Pipeline run enqueued", "run_id": "uuid" }
```

### `GET /runs`

List pipeline runs with pagination.

- **Query Params**: `status` (optional), `limit` (1-100, default 20), `offset` (default 0)

**Response**: `PaginatedResponse[PipelineRunResponse]`

```json
{
  "items": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### `GET /runs/{run_id}`

Get detailed run with nested OCR and post-processing results.

**Response**: `PipelineRunDetailResponse`

```json
{
  "id": "uuid",
  "input_image_path": "uploads/abc123.png",
  "status": "completed",
  "error_message": null,
  "created_at": "...",
  "completed_at": "...",
  "ocr_results": [
    {
      "id": "uuid",
      "model_name": "tesseract",
      "raw_text": " extracted text here ",
      "confidence": 0.85,
      "processing_time_ms": 1234,
      "error": null,
      "created_at": "...",
      "post_processing_results": [
        {
          "id": "uuid",
          "title_en": "One Piece",
          "title_ja": "ワンピース",
          "code": "9784088725093",
          "confidence": 0.92,
          "processing_type": "llm+rules",
          "raw_response": null,
          "extra_metadata": {"author": "Eiichiro Oda"},
          "created_at": "..."
        }
      ]
    }
  ]
}
```

### `POST /runs/{run_id}/cancel`

Cancel a pending or processing pipeline run.

- **Status check**: Returns 409 if status is `completed`, `failed`, or `cancelled`

**Response**:
```json
{ "message": "Pipeline run cancelled", "run_id": "uuid" }
```

The worker cooperatively checks for cancellation at checkpoints before setting `status=processing` and before calling `engine.process()`.

---

## Results (`/api/v1/results`)

### `GET /results`

List post-processing results with filtering.

- **Query Params**: `model_name`, `min_confidence`, `max_confidence`, `limit`, `offset`

**Response**: `PaginatedResponse[PostProcessingResultResponse]`

### `PUT /results/{result_id}/override`

Override title fields on a post-processing result. Changes propagate to the linked catalog entry (status → `needs_review`).

**Request**: `ResultOverrideRequest`
```json
{
  "title_en": "Corrected Title",
  "title_ja": null,
  "code": "978..."
}
```

**Response**: `PostProcessingResultResponse`

---

## Catalog (`/api/v1/catalog`)

### `GET /catalog`

List catalog entries with search.

- **Query Params**: `status`, `search` (case-insensitive ilike on title_en, title_ja, code), `limit`, `offset`

**Response**: `PaginatedResponse[CatalogEntryResponse]`

### `GET /catalog/export`

Export all catalog entries as CSV download.

**Response**: `text/csv` with `Content-Disposition: attachment`

### `GET /catalog/{entry_id}`

Get a single catalog entry.

### `PUT /catalog/{entry_id}`

Update a catalog entry.

**Request**: `CatalogUpdateRequest`
```json
{
  "status": "auto_confirmed",
  "title_en": "Updated Title",
  "title_ja": "更新タイトル",
  "code": "978..."
}
```

Valid statuses: `auto_confirmed`, `needs_review`, `rejected`

---

## Models (`/api/v1/models`)

### `GET /models`

List all OCR model configurations from the database.

**Response**: `list[ModelConfigResponse]`

```json
[
  {
    "id": "uuid",
    "model_name": "tesseract",
    "is_enabled": true,
    "parameters": {"psm": 3, "oem": 3},
    "language_hint": "eng+jpn",
    "updated_at": "..."
  }
]
```

### `PUT /models/{model_name}`

Update a model's runtime configuration.

**Request**: `ModelConfigUpdateRequest`
```json
{
  "is_enabled": true,
  "parameters": {"psm": 6},
  "language_hint": "jpn"
}
```

**Response**: `ModelConfigResponse`

---

## Preprocess (`/api/v1/preprocess`)

### `GET /preprocess/steps`

List all preprocessing step descriptors in canonical order.

**Response**: `list[StepDescriptorResponse]`

### `POST /preprocess/preview/step`

Preview a single preprocessing step on an image.

- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (image file), `step_name` (string), `params` (JSON string, default `"{}"`)

**Request**: `PreviewStepRequest`

**Response**: `PreviewStepResponse`
```json
{
  "image": "data:image/png;base64,...",
  "step_name": "binarize",
  "metadata": {},
  "processing_time_ms": 45,
  "success": true,
  "error": null
}
```

### `POST /preprocess/preview/pipeline`

Preview the full preprocessing pipeline, returning an image after each step.

- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (image file), `steps` (JSON string, default `"{}"`)

**Request**: `PreviewPipelineRequest`

**Response**: `PreviewPipelineResponse`

### `POST /preprocess/export`

Export pipeline config as YAML.

**Request**: `ExportPipelineRequest`
**Response**: `{"yaml": "..."}`

---

## OCR Playground (`/api/v1/ocr`)

### `GET /ocr/registry`

List all OCR model descriptors from the registry with availability status and DB enabled state.

**Response**: `list[ModelDescriptorResponse]`

```json
[
  {
    "name": "tesseract",
    "label": "Tesseract",
    "description": "Open-source OCR engine...",
    "params": [
      {"name": "languages", "type": "multiselect", "default": ["eng", "jpn"], ...}
    ],
    "available": true,
    "enabled": true
  }
]
```

### `POST /ocr/run`

Run a single OCR model on an image (playground mode).

- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (image file), `model_name` (string), `params` (JSON string, default `"{}"`), `enable_llm` (boolean, default false)

**Request**: `OCRRunRequest`

**Response**: `OCRRunResponse`
```json
{
  "ocr": {
    "raw_text": "extracted text",
    "model_name": "tesseract",
    "confidence": 0.85,
    "processing_time_ms": 1234,
    "error": null
  },
  "llm": null
}
```

### `POST /ocr/export`

Export OCR model config as YAML matching `ocrs.yaml` format.

---

## Quick Run (`/api/v1/run`)

### `POST /run/quick`

Run the full pipeline statelessly (no DB persistence). Optionally loads a profile as defaults.

- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (image file), `preprocess_steps` (JSON string), `ocr_models` (JSON string), `enable_llm` (boolean), `profile_id` (string, optional)

**Request**: `QuickRunRequest`

If `profile_id` is provided, the profile config is loaded as defaults and any inline fields override them.

**Response**: `QuickRunResponse`
```json
{
  "ocr_results": [
    {
      "raw_text": "extracted text",
      "model_name": "tesseract",
      "confidence": 0.85,
      "processing_time_ms": 1234,
      "error": null
    }
  ],
  "llm": {
    "title_en": "One Piece",
    "title_ja": "ワンピース",
    "code": "9784088725093",
    "confidence": 0.92,
    "source_method": "llm"
  },
  "total_processing_time_ms": 3500
}
```

---

## Batches (`/api/v1/batches`)

### `POST /batches`

Create a batch with multiple files. Optionally associate with a profile.

- **Content-Type**: `multipart/form-data`
- **Form Fields**: `files` (multiple), `name` (optional), `profile_id` (optional)

**Response**: `BatchRunDetailResponse` (201 Created)

```json
{
  "id": "uuid",
  "name": "Manga Volume 1",
  "status": "pending",
  "total_count": 5,
  "completed_count": 0,
  "failed_count": 0,
  "created_at": "...",
  "completed_at": null,
  "runs": [...]
}
```

### `POST /batches/{batch_id}/trigger`

Enqueue all pending runs in a batch.

- **Status check**: Returns 409 if batch is not `pending`

**Response**: `BatchRunResponse` (status updated to `processing`)

### `GET /batches`

List batches with pagination.

- **Query Params**: `status`, `limit`, `offset`

**Response**: `PaginatedResponse[BatchRunResponse]`

### `GET /batches/{batch_id}`

Get batch detail with nested runs.

**Response**: `BatchRunDetailResponse`

---

## Profiles (`/api/v1/profiles`)

### `POST /profiles`

Create a new pipeline profile.

**Request**: `ProfileCreateRequest`
```json
{
  "name": "Manga High Quality",
  "description": "Full preprocessing + Tesseract + LLM",
  "preprocess_steps": {
    "grayscale": {"enabled": true},
    "upscale": {"enabled": true, "method": "cubic", "scale_factor": 2},
    "denoise": {"enabled": true, "method": "gaussian", "strength": "light"},
    "binarize": {"enabled": true, "method": "otsu"}
  },
  "ocr_models": {
    "tesseract": {"enabled": true, "languages": ["eng", "jpn"], "psm": 6, "oem": 3}
  },
  "enable_llm": true,
  "is_default": false
}
```

**Response**: `ProfileResponse` (201 Created)

### `GET /profiles`

List all profiles.

- **Query Params**: `limit` (default 50), `offset` (default 0)

**Response**: `PaginatedResponse[ProfileResponse]`

### `GET /profiles/{profile_id}`

Get a single profile.

**Response**: `ProfileResponse`

### `PUT /profiles/{profile_id}`

Update a profile (partial update — only sent fields are changed).

**Request**: `ProfileUpdateRequest`

**Response**: `ProfileResponse`

### `DELETE /profiles/{profile_id}`

Delete a profile. Returns 204 No Content on success.

### `POST /profiles/{profile_id}/set-default`

Set a profile as the default. Unsets any previous default.

**Response**: `ProfileResponse`

### `POST /profiles/import`

Import a profile from JSON with validation.

**Request**: `ProfileImportRequest`
```json
{
  "name": "Imported Profile",
  "description": "Profile imported from external config",
  "preprocess_steps": {
    "grayscale": {"enabled": true},
    "binarize": {"enabled": true, "method": "otsu"}
  },
  "ocr_models": {
    "tesseract": {"enabled": true, "languages": ["eng", "jpn"]}
  },
  "enable_llm": true,
  "is_default": false
}
```

**Response**: `ProfileResponse` (201 Created)

### `GET /profiles/{profile_id}/export`

Export a profile as a downloadable JSON file.

**Response**: `application/json` with `Content-Disposition: attachment; filename="<profile_name>.json"`

### `POST /profiles/{profile_id}/duplicate`

Duplicate an existing profile. The new profile has the same configuration with ` (copy)` appended to the name.

**Response**: `ProfileResponse` (201 Created)

---

## Ollama (`/api/v1/ollama`)

### `GET /ollama/status`

Get the current Ollama configuration and connectivity status.

**Response**: `OllamaStatusResponse`
```json
{
  "configured": true,
  "base_url": "http://localhost:11434",
  "default_model": "llama3",
  "default_vision_model": "llava"
}
```

### `GET /ollama/models`

List available text-generation models from the connected Ollama instance.

**Response**: `list[OllamaLLMModelResponse]`
```json
[
  {
    "name": "llama3",
    "size": 4661224676,
    "modified_at": "2026-04-28T12:00:00Z"
  }
]
```

### `GET /ollama/vision-models`

List available vision-capable models from the connected Ollama instance.

**Response**: `list[OllamaVisionModelResponse]`
```json
[
  {
    "name": "llava",
    "size": 4799999904,
    "modified_at": "2026-04-28T12:00:00Z"
  }
]
```

---

## LLM (`/api/v1/llm`)

### `GET /llm/providers`

List available LLM providers and their availability status.

**Response**: `LLMProvidersResponse`
```json
{
  "providers": [
    {
      "name": "openrouter",
      "label": "OpenRouter",
      "available": true
    },
    {
      "name": "ollama",
      "label": "Ollama (Local)",
      "available": false
    }
  ]
}
```

### `GET /llm/models`

List available LLM models with their capabilities.

**Response**: `list[LLMModelInfo]`
```json
[
  {
    "id": "openai/gpt-oss-1",
    "label": "GPT-oss-1",
    "supports_json_mode": true
  },
  {
    "id": "anthropic/claude-sonnet-4",
    "label": "Claude Sonnet 4",
    "supports_json_mode": true
  }
]
```

---

## Settings (`/api/v1/settings`)

### `GET /settings/credentials/{service}`

Check whether a credential (API key) is configured for a given service.

- **Path Params**: `service` — service name (e.g. `openrouter`, `ollama`)

**Response**:
```json
{
  "has_key": true
}
```

### `PUT /settings/credentials/{service}`

Set or update the API key for a service.

- **Path Params**: `service` — service name

**Request**:
```json
{
  "api_key": "sk-or-v1-..."
}
```

**Response**: `204 No Content`

### `DELETE /settings/credentials/{service}`

Delete the stored credential for a service.

- **Path Params**: `service` — service name

**Response**: `204 No Content`

### `POST /settings/credentials/{service}/test`

Test the validity of the stored credential for a service by making a lightweight API call.

- **Path Params**: `service` — service name

**Response**:
```json
{
  "valid": true,
  "message": "Credential validated successfully"
}
```

### `GET /settings/ollama`

Get the current Ollama configuration.

**Response**:
```json
{
  "base_url": "http://localhost:11434",
  "default_model": "llama3",
  "default_vision_model": "llava"
}
```

### `PUT /settings/ollama`

Update the Ollama configuration.

**Request**:
```json
{
  "base_url": "http://192.168.1.100:11434",
  "default_model": "mistral",
  "default_vision_model": "bakllava"
}
```

**Response**:
```json
{
  "base_url": "http://192.168.1.100:11434",
  "default_model": "mistral",
  "default_vision_model": "bakllava"
}
```

### `POST /settings/ollama/ping`

Ping the configured Ollama instance to verify connectivity.

**Response**:
```json
{
  "reachable": true,
  "latency_ms": 12
}
```

---

## Common Response Schemas

### `PaginatedResponse[T]`

```json
{
  "items": [T],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### `PipelineRunResponse`

```json
{
  "id": "uuid",
  "input_image_path": "string",
  "status": "pending | processing | completed | failed | cancelled",
  "error_message": "string | null",
  "created_at": "datetime",
  "completed_at": "datetime | null"
}
```

### `PipelineRunDetailResponse`

Extends `PipelineRunResponse` with:
```json
{
  "ocr_results": [OCRResultDetailResponse]
}
```

### `PostProcessingResultResponse`

```json
{
  "id": "uuid",
  "title_en": "string | null",
  "title_ja": "string | null",
  "code": "string | null",
  "confidence": 0.92,
  "processing_type": "llm+rules",
  "raw_response": "string | null",
  "extra_metadata": "object | null",
  "created_at": "datetime"
}
```

### `BatchRunResponse`

```json
{
  "id": "uuid",
  "name": "string | null",
  "status": "pending | processing | completed | partial_failure | failed | cancelled",
  "total_count": 5,
  "completed_count": 3,
  "failed_count": 1,
  "created_at": "datetime",
  "completed_at": "datetime | null"
}
```

### `ProfileResponse`

```json
{
  "id": "uuid",
  "name": "string",
  "description": "string | null",
  "preprocess_steps": {"step_name": {"param": "value"}} | null,
  "ocr_models": {"model_name": {"param": "value"}} | null,
  "enable_llm": true,
  "is_default": false,
  "created_at": "datetime",
  "updated_at": "datetime | null"
}
```

### `OllamaStatusResponse`

```json
{
  "configured": true,
  "base_url": "string | null",
  "default_model": "string | null",
  "default_vision_model": "string | null"
}
```

### `OllamaLLMModelResponse`

```json
{
  "name": "string",
  "size": 0,
  "modified_at": "datetime | null"
}
```

### `OllamaVisionModelResponse`

```json
{
  "name": "string",
  "size": 0,
  "modified_at": "datetime | null"
}
```

### `LLMProvidersResponse`

```json
{
  "providers": [
    {
      "name": "string",
      "label": "string",
      "available": true
    }
  ]
}
```

### `LLMModelInfo`

```json
{
  "id": "string",
  "label": "string",
  "supports_json_mode": true
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Human-readable error message",
  "error_code": "error_type"
}
```

### HTTP Status Codes

| Status | Error Code | When |
|---|---|---|
| 400 | `permanent_error` | File not found, invalid input |
| 400 | — | Validation errors (FastAPI default) |
| 404 | — | Resource not found |
| 409 | — | Duplicate name, already triggered |
| 422 | — | Invalid request body |
| 500 | `configuration_error` | Bad config file |
| 500 | `internal_error` | Unhandled MangaOCRError |
| 502 | `llm_extraction_error` | LLM API failure |
| 503 | `model_not_available` | OCR model deps missing |

---

## OpenAPI / Swagger

The auto-generated OpenAPI 3.0 spec is available at:

- **Swagger UI**: `GET /api/docs`
- **OpenAPI JSON**: `GET /api/openapi.json`

The spec is generated by FastAPI from the route definitions and Pydantic schemas. It includes:
- All endpoint descriptions
- Request body schemas with validation rules
- Response schemas with examples
- Authentication info (none currently — no auth layer)
