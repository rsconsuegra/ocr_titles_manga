# Phase 2 User Stories: Multi-Model + Prompt Management

These user stories cover Phase 2 (Multi-Model + Prompt Management), excluding sub-phase 2D (Social Media URL Input). They are organized by sub-phase: OCR Models (2A), Agenta + Prompt Management (2B), Pipeline Visualization (2C).

---

## US-2A1: Run PaddleOCR for Manga Text Extraction

> As an operator, I want PaddleOCR to be available as an OCR model in the pipeline so that I can leverage its multilingual capabilities for extracting text from manga images.

**Acceptance Criteria**:
- PaddleOCR model is listed in `GET /api/v1/models` with current enabled/disabled status
- When enabled, PaddleOCR runs during pipeline execution alongside other enabled models
- `is_available` returns `True` when the `paddleocr` Python package is installed, `False` otherwise
- Model supports configurable languages (EN, JA, CH, KO) via model config parameters
- Model supports GPU acceleration toggle via model config parameters
- First `run()` call lazy-loads the PaddleOCR model; subsequent calls reuse the loaded model
- Returns `OCRResult` with raw text, average confidence score, and processing time
- Gracefully handles corrupt images: returns `OCRResult` with empty text, confidence 0.0, and error message
- Falls back to CPU if CUDA is unavailable (logs warning)

---

## US-2A2: Run EasyOCR for Manga Text Extraction

> As an operator, I want EasyOCR to be available as an OCR model in the pipeline so that I can leverage its PyTorch-based multilingual OCR for extracting text from manga images.

**Acceptance Criteria**:
- EasyOCR model is listed in `GET /api/v1/models` with current enabled/disabled status
- When enabled, EasyOCR runs during pipeline execution alongside other enabled models
- `is_available` returns `True` when the `easyocr` Python package is installed, `False` otherwise
- Model supports configurable languages (EN, JA, CH, KO) via model config parameters
- Model supports GPU toggle via model config parameters
- First `run()` call lazy-loads the EasyOCR reader; subsequent calls reuse it
- Returns `OCRResult` with raw text, per-word averaged confidence, and processing time
- Gracefully handles corrupt images: returns `OCRResult` with empty text, confidence 0.0, and error message

---

## US-2A3: Run Vision API Model for Manga Text Extraction

> As an operator, I want to use any OpenAI-compatible vision API (OpenRouter, ZhipuAI, etc.) as an OCR model in the pipeline so that I can leverage vision-language models for extracting text from complex manga layouts.

**Acceptance Criteria**:
- Vision API model appears as "GLM OCR" in `GET /api/v1/models`
- `is_available` returns `True` when `api_endpoint` is configured in model parameters, `False` otherwise
- When enabled, sends image as base64 to the configured endpoint using OpenAI chat completions format
- Configurable via model parameters: `api_endpoint`, `api_key`, `model`, `prompt`, `max_tokens`, `temperature`
- If `api_key` is empty, falls back to the OpenRouter API key from `configs.toml`
- Returns `OCRResult` with the model's response as `raw_text`, confidence 0.8 for non-empty responses
- Handles API errors: timeout, rate limit (429), authentication failure — returns `OCRResult` with error message
- No model download required (pure API client)

---

## US-2B1: Sync Prompts with Agenta.ai

> As an operator, I want prompt versions to sync bidirectionally with Agenta.ai so that Agenta is the single source of truth for prompt content and I can manage prompts from either the Agenta dashboard or the Manga OCR UI.

**Acceptance Criteria**:
- `POST /api/v1/prompts/sync` triggers bidirectional sync
- Pull: fetches all prompts from Agenta, creates or updates `prompt_versions` rows in DB
- Push: sends any local-only prompt versions (no `agenta_id`) to Agenta, stores returned ID
- Conflict resolution: if timestamps differ, Agenta version wins (Agenta is source of truth)
- Sync returns summary: `{pulled: N, pushed: N, conflicts: N, errors: [...]}`
- If Agenta is not configured (missing API key/base URL/app ID), sync returns 503 with message
- If Agenta is unreachable, sync returns error details but does not crash; local DB unchanged
- Optional: `AGENTA_SYNC_ON_STARTUP=true` triggers sync automatically when API server starts

---

## US-2B2: Create and Edit Prompt Versions

> As an operator, I want to create new prompt versions and edit existing ones via the API and UI so that I can iterate on LLM extraction quality.

**Acceptance Criteria**:
- `POST /api/v1/prompts` creates a new prompt version with auto-incremented `version_number`
- `PUT /api/v1/prompts/{id}` updates content and tags of an existing version
- Frontend `/prompts/new` provides a markdown editor with live preview for creating prompts
- Frontend `/prompts/:id/edit` allows editing existing prompt content
- Creating a new version does NOT automatically activate it (must explicitly activate)
- If Agenta is configured, create/update pushes the version to Agenta in the background
- Prompt content validation: required, 1-50,000 characters
- Version numbers are unique per `prompt_type`

---

## US-2B3: Activate and Manage Prompt Versions

> As an operator, I want to activate a specific prompt version for use in the pipeline so that I can control which prompt is used for LLM extraction.

**Acceptance Criteria**:
- `POST /api/v1/prompts/{id}/activate` activates the specified version and deactivates all others of the same `prompt_type`
- Only one prompt version per type can be active at a time
- Active prompt is used by the worker for LLM extraction in new pipeline runs
- Frontend shows active status with a teal LED indicator
- Deleting an active prompt version returns 409 "Cannot delete active prompt"
- Deleting an inactive, unreferenced version performs hard delete
- Deleting a version referenced by `post_processing_results` performs soft delete (deactivate only)
- Frontend `/prompts` page lists all versions with active/inactive status

---

## US-2B4: Compare Prompt Versions

> As an operator, I want to compare two prompt versions side-by-side so that I can see what changed between iterations and evaluate whether the changes are appropriate.

**Acceptance Criteria**:
- `GET /api/v1/prompts/{id}/diff/{other_id}` returns unified diff between two versions
- Diff shows added lines (green), removed lines (red), and unchanged lines
- Both versions must have the same `prompt_type` (returns 400 if mismatched)
- Returns 404 if either version ID does not exist
- Frontend `/prompts/:id/diff/:otherId` shows side-by-side diff view
- Diff page has a dropdown to change the comparison version
- Line numbers shown for both versions

---

## US-2B5: Browse Prompt Version History

> As an operator, I want to see the full history of prompt versions with metadata so that I can understand the evolution of prompts and find specific versions.

**Acceptance Criteria**:
- `GET /api/v1/prompts` returns paginated list of all prompt versions
- Filterable by `prompt_type` via query parameter
- Sorted by `version_number` descending (newest first)
- Each entry shows: version number, content (truncated), active status, source (local/agenta), tags, created date
- Frontend `/prompts` page displays the list with DSO dark theme table
- Pagination controls for lists exceeding 50 items
- "Sync with Agenta" button visible at top (disabled if Agenta not configured)
- Click a version to view full details at `/prompts/:id`

---

## US-2B6: Track Which Prompt Version Produced Each Result

> As an operator, I want every post-processing result to record which prompt version was used so that I can correlate extraction quality with specific prompt iterations.

**Acceptance Criteria**:
- Worker loads the active prompt from `prompt_versions` table before running pipeline
- `LLMExtractor` receives prompt content from the worker (not loaded from file)
- `PostProcessingResult.prompt_version_id` is populated for all new pipeline runs
- Run detail API response includes `prompt_version_id` in each post-processing result
- Frontend run detail page shows which prompt version was used for each extraction
- If no active prompt in DB, falls back to file-based prompt with `prompt_version_id=NULL`

---

## US-2C1: View Interactive Pipeline Diagram

> As an operator, I want to see a visual diagram of the OCR pipeline showing all processing stages so that I understand the data flow and can identify which models and prompts are being used.

**Acceptance Criteria**:
- Pipeline diagram renders as a left-to-right directed graph with 6 nodes: Input → OCR Models → Text Aggregation → LLM → Rules → Output
- Each node has an icon, label, and brief status text
- Diagram supports zoom and pan
- Node colors indicate status: gray (idle), teal with breathing animation (processing), teal solid (completed), amber (error)
- Diagram renders on the Run Detail page below the run header
- When viewing a completed run, nodes show real data (model names, text counts, extracted titles)
- When no run data, shows a static diagram with currently configured models

---

## US-2C2: Inspect Pipeline Node Configuration

> As an operator, I want to click on a pipeline diagram node to see its detailed configuration so that I can understand exactly what parameters and models are being used at each stage.

**Acceptance Criteria**:
- Clicking a node opens a detail panel (NodeConfigPanel) on the right side
- Node details vary by type:
  - **Input node**: image path, source platform, upload date
  - **OCR Models node**: list of enabled models with parameters (language, GPU, PSM, etc.)
  - **LLM node**: prompt version number, model name, content preview (first 200 chars)
  - **Rules node**: regex patterns applied, normalization rules
  - **Output node**: extracted title_en, title_ja, code, confidence score
- Panel has a close button (X) to dismiss
- Panel uses DSO dark theme styling
- When viewing a run, shows actual runtime values; otherwise shows config defaults

---

## US-2C3: View Pipeline Status on Dashboard

> As an operator, I want to see a compact version of the pipeline diagram on the dashboard so that I can quickly see which models and prompts are currently configured.

**Acceptance Criteria**:
- Dashboard includes a compact pipeline diagram in the bottom-left "Tactical Controls" section
- Compact diagram shows the 6 pipeline nodes in a smaller format
- Each node shows a label and current configuration (enabled model names, active prompt version)
- No click interactivity on the compact version (informational only)
- Diagram updates when model configs or prompt versions change (on page load)
- Uses same DSO node styling as the full diagram but with smaller dimensions

---

## User Story Numbering Summary

| ID | Sub-Phase | Title |
|----|-----------|-------|
| US-2A1 | OCR Models | Run PaddleOCR for Manga Text Extraction |
| US-2A2 | OCR Models | Run EasyOCR for Manga Text Extraction |
| US-2A3 | OCR Models | Run Vision API Model for Manga Text Extraction |
| US-2B1 | Agenta + Prompts | Sync Prompts with Agenta.ai |
| US-2B2 | Agenta + Prompts | Create and Edit Prompt Versions |
| US-2B3 | Agenta + Prompts | Activate and Manage Prompt Versions |
| US-2B4 | Agenta + Prompts | Compare Prompt Versions |
| US-2B5 | Agenta + Prompts | Browse Prompt Version History |
| US-2B6 | Agenta + Prompts | Track Which Prompt Version Produced Each Result |
| US-2C1 | Visualization | View Interactive Pipeline Diagram |
| US-2C2 | Visualization | Inspect Pipeline Node Configuration |
| US-2C3 | Visualization | View Pipeline Status on Dashboard |

**Total: 12 user stories across 3 sub-phases** (2D excluded as requested).
