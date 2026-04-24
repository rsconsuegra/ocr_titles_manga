# V2 User Stories: MVP Backend API

These user stories cover Phase 1 (MVP Backend API). They are organized by sub-phase: Database (1A), API Routes (1B), Task Queue (1C), and Frontend (1D).

---

## US-1A1: Store Pipeline Runs in Database

> As an operator, I want every OCR pipeline execution to be recorded in PostgreSQL so that I can review past runs, track success rates, and audit processing history.

**Acceptance Criteria**:
- Uploading an image creates a `pipeline_runs` row with status="pending"
- Worker updates status through pending -> processing -> completed/failed
- `completed_at` is set when status becomes "completed" or "failed"
- `error_message` is populated when status is "failed"
- Each run has a unique UUID primary key
- Runs are queryable by status and sortable by `created_at`

---

## US-1A2: Seed Model Configurations

> As an operator, I want the database to be pre-populated with model configurations for tesseract, paddle, easyocr, and glm_ocr so that the system works out of the box after migration.

**Acceptance Criteria**:
- Alembic seed migration inserts 4 rows into `model_configs`
- Tesseract is enabled by default; paddle, easyocr, glm_ocr are disabled
- Each model config includes default parameters matching `ocrs.yaml`
- `model_name` is unique across all rows
- Running `make migrate` on a fresh database produces these rows

---

## US-1A3: Store Prompt Versions

> As an operator, I want the LLM extraction prompt to be stored in the database so that future prompt iterations can be tracked and compared.

**Acceptance Criteria**:
- Alembic seed migration reads `prompts/llm/extract_title_v1.md` and inserts into `prompt_versions`
- The prompt has `prompt_type="llm"`, `version_number=1`, `is_active=True`
- Worker loads the active prompt from the database (falls back to file if DB has none)
- Multiple prompt versions can coexist; only one is active per type

---

## US-1B1: Upload Images via API

> As an operator, I want to upload manga images via a REST API endpoint so that I can submit images for processing without using the CLI.

**Acceptance Criteria**:
- `POST /api/v1/inputs/upload` accepts 1-10 image files as multipart form data
- Accepted formats: PNG, JPG, WEBP, TIFF, BMP
- Max file size: 20MB per file
- Files are saved to `uploads/` with UUID filenames
- A `pipeline_runs` row is created per image with status="pending" and source_platform="manual"
- Response returns list of created `PipelineRunResponse` with IDs and statuses
- Returns 400 for invalid format, file too large, or too many files
- Returns 422 for missing files

---

## US-1B2: Trigger Pipeline Execution

> As an operator, I want to trigger OCR processing for an uploaded image via the API so that the pipeline runs asynchronously in the background.

**Acceptance Criteria**:
- `POST /api/v1/pipeline/run/{run_id}` enqueues a Dramatiq job
- Returns 404 if run_id does not exist
- Returns 409 if run status is not "pending" (already triggered)
- After triggering, the run transitions through: pending -> processing -> completed/failed
- Multiple triggers for the same run_id are idempotent (return 409 after first trigger)

---

## US-1B3: View Pipeline Run History

> As an operator, I want to list all pipeline runs with their statuses so that I can monitor processing and find specific runs.

**Acceptance Criteria**:
- `GET /api/v1/pipeline/runs` returns paginated list of runs (default 20 per page)
- Runs are sorted by `created_at` descending (newest first)
- Filterable by status: `?status=completed`
- Response includes: id, input_image_path, status, created_at, completed_at
- Pagination via `limit` and `offset` query params
- Total count included in response

---

## US-1B4: Inspect Run Details

> As an operator, I want to view the full details of a pipeline run including all OCR results and extracted data so that I can evaluate the quality of extraction.

**Acceptance Criteria**:
- `GET /api/v1/pipeline/runs/{run_id}` returns full run details
- Includes all `ocr_results`: model_name, raw_text, confidence, processing_time_ms, error
- Includes all `post_processing_results`: title_en, title_ja, code, confidence, processing_type
- Returns 404 if run_id does not exist
- Response includes run metadata: status, timestamps, error_message

---

## US-1B5: Browse Extraction Results

> As an operator, I want to browse all post-processing results across runs so that I can review extraction quality at a glance.

**Acceptance Criteria**:
- `GET /api/v1/results` returns paginated list of post-processing results
- Filterable by `model_name`, `min_confidence`, `max_confidence`
- Each result includes: title_en, title_ja, code, confidence, processing_type, created_at
- `PUT /api/v1/results/{result_id}/override` allows manual correction of title_en, title_ja, code
- Override updates the linked catalog entry if one exists
- Returns 404 if result_id does not exist

---

## US-1B6: Manage Catalog Entries

> As an operator, I want to browse, search, filter, and update catalog entries so that I can curate a clean list of extracted manga titles.

**Acceptance Criteria**:
- `GET /api/v1/catalog` returns paginated list of catalog entries
- Searchable by title_en, title_ja, code via `?search=...` query param
- Filterable by status: `?status=needs_review`
- `PUT /api/v1/catalog/{entry_id}` updates status (auto_confirmed/needs_review/rejected), title fields, code
- `GET /api/v1/catalog/export` downloads all entries as CSV
- CSV columns: id, title_en, title_ja, code, status, confidence, source_run_id, created_at, updated_at
- Returns 404 for nonexistent entry_id

---

## US-1B7: Configure Models via API

> As an operator, I want to enable/disable OCR models and adjust parameters via the API so that I can control the pipeline without editing config files.

**Acceptance Criteria**:
- `GET /api/v1/models` returns all 4 model configs with current settings
- `PUT /api/v1/models/{model_name}` updates is_enabled, parameters, language_hint
- Changes take effect on the next pipeline run (worker reads fresh config from DB)
- Returns 404 if model_name does not exist
- Returns validation error for invalid parameter values

---

## US-1C1: Process OCR Jobs Asynchronously

> As an operator, I want OCR processing to happen in a background worker so that the API remains responsive during long-running pipeline executions.

**Acceptance Criteria**:
- Dramatiq worker runs as a separate process from the API server
- Worker connects to Redis for job queue
- Worker processes jobs: loads config, runs OCREngine, stores results in database
- OCR results are stored in `ocr_results` table
- Post-processing results (LLM + rules) are stored in `post_processing_results` table
- Catalog entry created automatically when extraction confidence > 0.0
- Worker logs progress: run_id, model_name, processing time, confidence
- Pipeline status transitions: pending -> processing -> completed (or failed)

---

## US-1C2: Retry Failed Pipeline Runs

> As an operator, I want transient failures (LLM API timeout, database connection) to be retried automatically so that temporary issues don't require manual intervention.

**Acceptance Criteria**:
- Failed jobs are retried up to 3 times with exponential backoff (10s, 30s, 60s)
- LLM API errors (5xx, timeout) trigger retry
- Database connection errors trigger retry
- OCR model errors do NOT trigger retry (captured in OCRResult, pipeline continues)
- Image not found does NOT trigger retry (permanent error)
- After all retries exhausted, run status is set to "failed" with error_message
- Retry count is visible in Dramatiq dashboard (or logs)

---

## US-1D1: Upload Images via Web UI

> As an operator, I want to upload manga images through a web browser so that I can submit images for OCR processing without using command-line tools.

**Acceptance Criteria**:
- `/upload` page shows drag-and-drop area and file picker
- Accepts 1-10 images with type validation (PNG, JPG, WEBP, TIFF, BMP)
- Shows preview thumbnails for selected files
- Submit button uploads files and displays created run IDs
- Each run has a "Trigger Pipeline" button
- After triggering, status badge updates to "processing"
- Shows error messages for invalid files or upload failures

---

## US-1D2: View Pipeline Run History in UI

> As an operator, I want to see a list of all pipeline runs in the web UI so that I can monitor processing status at a glance.

**Acceptance Criteria**:
- `/runs` page shows table of runs: ID, image path, status badge, created_at
- Status badges are color-coded: pending (gray), processing (blue), completed (green), failed (red)
- Status filter dropdown filters visible runs
- Pagination controls for large lists
- Click a row to navigate to run detail page

---

## US-1D3: Inspect Run Details in UI

> As an operator, I want to view the full details of a pipeline run in the web UI so that I can evaluate OCR quality and extracted metadata.

**Acceptance Criteria**:
- `/runs/:id` page shows input image preview
- Per-model OCR results displayed: model name, raw text, confidence meter, processing time
- Post-processing results: extracted title_en, title_ja, code with confidence meter
- Confidence meters are color-coded: red (<0.3), yellow (0.3-0.7), green (>0.7)
- Manual override form allows editing title_en, title_ja, code
- Override saved via API, confirmation message shown

---

## US-1D4: Browse Catalog in UI

> As an operator, I want to browse and manage the catalog of extracted manga titles in the web UI so that I can curate and export the data.

**Acceptance Criteria**:
- `/catalog` page shows table: title_en, title_ja, code, confidence meter, status badge, created_at
- Search input filters entries by title or code
- Status filter dropdown (auto_confirmed/needs_review/rejected)
- Click a row to expand: source run link, editable fields, status dropdown
- Save changes updates entry via API
- "Export CSV" button downloads all entries as a CSV file
- Pagination for large catalogs
