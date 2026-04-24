# Product Requirements Document: Manga OCR

**Version**: 1.0  
**Date**: 2026-04-21  
**Status**: Approved  

---

## 1. Executive Summary

### Problem Statement

Manga readers share title references, codes, and identifiers on social media platforms (X/Twitter, Facebook), but these are embedded in images — screenshots, photos of manga pages, promotional art, and storefront listings. There is no automated way to extract, normalize, and catalog these references into a structured manga database.

### Proposed Solution

A three-tier system (React + TypeScript frontend, Python FastAPI backend, Python OCR engine) that ingests social media post images, runs them through multiple OCR models in parallel, post-processes raw text via OpenRouter LLM + rule-based matching, and produces structured manga catalog entries. Includes prompt versioning via Agenta.ai and a results comparison viewer for evaluating model/prompt performance.

### Success Criteria

| # | Metric | Target |
|---|--------|--------|
| 1 | OCR extraction accuracy on EN + JA manga text | >= 80% correct title/code extraction |
| 2 | End-to-end processing latency per image (all models) | <= 30 seconds |
| 3 | Results viewer comparison | Side-by-side for >= 2 model/prompt combinations |
| 4 | Throughput on single VPS | >= 50 posts/day |
| 5 | Prompt CRUD propagation to Agenta.ai | Within 10 seconds |

---

## 2. User Experience & Functionality

### 2.1 User Personas

| Persona | Description |
|---------|-------------|
| **Operator** | Single user (project owner). Configures the pipeline, manages prompts, reviews OCR results, and curates the manga catalog. Self-hosted, single-VPS deployment. |

### 2.2 User Stories

#### US-1: Pipeline Visualization

> As an operator, I want to see a visual flowchart of the OCR pipeline (input -> OCR models -> post-processing -> output) so that I understand data flow and can identify bottlenecks.

**Acceptance Criteria**:
- Pipeline diagram renders as a directed graph with nodes for each processing stage
- Each node shows current status (idle / processing / error) with real-time updates
- Clicking a node shows its configuration (model name, prompt version, parameters)
- Pipeline stages: Input Source -> OCR Model(s) -> Raw Text Aggregation -> LLM Post-Processing -> Rule-Based Matching -> Structured Output

#### US-2: Prompt Version Management

> As an operator, I want to create, read, update, and delete prompt versions for both OCR model configuration and LLM post-processing so that I can iterate on extraction quality.

**Acceptance Criteria**:
- CRUD interface for two prompt categories: OCR model prompts and LLM post-processing prompts
- Each prompt version stored with: version number, content, created_at, tags/labels, is_active flag
- Agenta.ai is the source of truth; local file copies synced from Agenta.ai
- Prompt versions can be activated/deactivated; only active prompts used in pipeline
- Diff view between any two prompt versions

#### US-3: Results Viewer

> As an operator, I want to compare OCR results across different model and prompt version combinations so that I can evaluate which configuration produces the best extraction quality.

**Acceptance Criteria**:
- Results table with columns: input image, OCR model, prompt version, raw text, post-processed text, extracted manga title/code, confidence score, timestamp
- Side-by-side comparison view for 2+ results from the same input image
- Filter by: OCR model, prompt version, date range, confidence threshold
- Sort by: confidence score, timestamp
- Manual correction override: operator can edit extracted title/code and mark as "ground truth"

#### US-4: Model Management

> As an operator, I want to enable/disable OCR models and configure their parameters so that I can control which models run in the pipeline.

**Acceptance Criteria**:
- List of available OCR models with toggle to enable/disable each
- Each model has configurable parameters: language hint, resolution, preprocessing options
- Model health status indicator (available / unavailable / error)
- Models: manga-ocr, Tesseract, PaddleOCR, EasyOCR, GLM OCR

#### US-5: Input Ingestion

> As an operator, I want to submit social media post images from X/Twitter, Facebook, or manual upload so that they enter the OCR pipeline.

**Acceptance Criteria**:
- Manual image upload via drag-and-drop or file picker
- URL input for X/Twitter and Facebook post links (image extracted server-side)
- Image preview before submission
- Bulk upload support (up to 10 images at once)
- Queue status indicator showing pending / processing / complete

#### US-6: Manga Catalog

> As an operator, I want to view and manage the extracted manga catalog so that I have a searchable database of manga references.

**Acceptance Criteria**:
- Catalog table: manga title (EN), manga title (JA), code/ISBN, source post URL, extraction date, confidence, status (auto-confirmed / needs-review / rejected)
- Search by title (EN/JA) or code
- Filter by status and date range
- Export to CSV

### 2.3 Non-Goals

- **Not** building a public-facing web application — single-user, self-hosted tool
- **Not** building automated social media scraping/scheduling — operator submits posts manually or via URL
- **Not** building a manga reading/streaming platform
- **Not** supporting languages beyond English and Japanese in v1
- **Not** building real-time streaming OCR — batch processing model
- **Not** building user authentication/authorization — single operator

---

## 3. AI System Requirements

### 3.1 OCR Model Pipeline

| Model | Role | Languages | Status | Notes |
|-------|------|-----------|--------|-------|
| manga-ocr | Primary manga text extraction | Japanese | v1 | Specialized for manga speech bubbles and overlays |
| Tesseract | Baseline general-purpose OCR | EN + JA | v1 | Configurable via `ocrs.yaml` |
| PaddleOCR | Alternative general OCR | EN + JA | Stub | Good multilingual support |
| EasyOCR | Alternative general OCR | EN + JA | Stub | PyTorch-based, easy to extend |
| GLM OCR | Vision-language model OCR | EN + JA | Stub | API-based, higher accuracy for complex layouts |

### 3.2 Post-Processing Pipeline

**Stage 1 — LLM Cleanup & Extraction**:
- Input: raw OCR text from each model
- Task: clean noise, extract manga title/code, normalize formatting
- LLM prompt versioned via Agenta.ai, local copy in `prompts/llm/`
- LLM provider: OpenRouter (model configurable in `configs.toml`)
- Output: structured JSON `{title_en, title_ja, code, confidence, raw_text_cleaned}`

**Stage 2 — Rule-Based Matching**:
- Input: LLM-extracted structured data
- Rules: regex patterns for ISBN formats, known manga code patterns, title normalization
- Cross-reference with existing catalog to detect duplicates
- Output: final structured entry with deduplication flag

### 3.3 Evaluation Strategy

- **Gold Standard Dataset**: Operator manually labels 50+ social media images with correct manga title/code
- **Metrics**:
  - Extraction accuracy: % of images where correct title/code is extracted (target >= 80%)
  - Per-model accuracy: compare each OCR model's contribution
  - Per-prompt-version accuracy: compare prompt iteration impact
- **Regression Testing**: Re-run gold standard dataset on every prompt version change; results stored in DB for comparison
- **Manual Review Queue**: Low-confidence extractions (< 70% confidence) flagged for operator review

### 3.4 Tool Requirements

| Tool | Purpose |
|------|---------|
| Agenta.ai | Prompt version management, source of truth for prompts |
| OpenRouter | LLM API for post-processing (multi-model access) |
| GLM OCR API | Vision-language model OCR (future) |
| Hugging Face | manga-ocr model weights |
| Tesseract / PaddleOCR / EasyOCR | Local OCR engines |

---

## 4. Technical Specifications

### 4.1 Architecture Overview

```
+-------------------------------------------------------------+
|                    Frontend (React + TS)                      |
|  +----------+ +-----------+ +----------+ +-----------+      |
|  | Pipeline | |  Prompt   | | Results  | |   Model   |      |
|  |  Viewer  | |  Manager  | |  Viewer  | |  Manager  |      |
|  +----------+ +-----------+ +----------+ +-----------+      |
+-----------------------------+-------------------------------+
                              | REST API
+-----------------------------v-------------------------------+
|                  Backend API (FastAPI, Python)               |
|  +----------+ +-----------+ +----------+ +-----------+      |
|  |  Input   | |  Pipeline | | Results  | |  Catalog  |      |
|  |  Ingest  | |  Orchestr.| |  Store   | |  Service  |      |
|  +----------+ +-----------+ +----------+ +-----------+      |
|                +-----------+ +-----------+                   |
|                |  Agenta   | |    LLM    |                   |
|                |  Client   | |  Client   |                   |
|                +-----------+ +-----------+                   |
+----------+------------------+--------------------------------+
           |                  |
+----------v---+  +-----------v--------------------------------+
|  PostgreSQL  |  |         OCR Engine (Python)                |
|              |  |  +--------+ +---------+ +--------------+  |
|  - catalog   |  |  | manga  | |Tesseract| |PaddleOCR     |  |
|  - results   |  |  |  ocr   | |         | |EasyOCR (stub)|  |
|  - prompts   |  |  +--------+ +---------+ +--------------+  |
|  - models    |  |  +------------------------------------+   |
|  - pipeline  |  |  |         GLM OCR (stub, API)         |   |
|    runs      |  |  +------------------------------------+   |
+--------------+  +-------------------------------------------+
```

### 4.2 Data Flow

1. **Input**: Operator submits image (upload or URL) via Frontend
2. **Ingest**: Backend downloads/saves image, creates pipeline run record, enqueues job via Dramatiq
3. **OCR**: Pipeline orchestrator sends image to each enabled OCR model (parallel execution)
4. **Aggregate**: Raw text outputs collected from all models
5. **LLM Post-Process**: Each raw text sent to OpenRouter LLM with active prompt version for cleanup/extraction
6. **Rule-Based Match**: Structured outputs run through regex/dedup rules
7. **Store**: Final results stored in PostgreSQL with all metadata (model, prompt version, confidence, timestamps)
8. **Display**: Frontend polls or receives WebSocket update with results

### 4.3 Database Schema (PostgreSQL)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `pipeline_runs` | Track each processing run | id, input_image_path, source_url, source_platform, status, created_at, completed_at |
| `ocr_results` | Raw OCR model output | id, pipeline_run_id, model_name, raw_text, processing_time_ms, created_at |
| `post_processing_results` | LLM + rule-based output | id, ocr_result_id, prompt_version_id, title_en, title_ja, code, confidence, processing_type, created_at |
| `prompt_versions` | Prompt version history | id, prompt_type, content, version_number, agenta_id, is_active, tags, created_at |
| `catalog_entries` | Final manga catalog | id, title_en, title_ja, code, source_run_id, confidence, status, created_at |
| `model_configs` | OCR model parameters | id, model_name, is_enabled, parameters (JSONB), language_hint, updated_at |
| `gold_standard` | Evaluation dataset | id, image_path, expected_title_en, expected_title_ja, expected_code, created_at |

### 4.4 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Input** | | |
| POST | `/api/v1/inputs/upload` | Upload image(s) |
| POST | `/api/v1/inputs/url` | Submit social media URL |
| GET | `/api/v1/inputs/{id}` | Get input status |
| **Pipeline** | | |
| POST | `/api/v1/pipeline/run` | Trigger pipeline for input |
| GET | `/api/v1/pipeline/runs` | List pipeline runs |
| GET | `/api/v1/pipeline/runs/{id}` | Get run details + results |
| **Prompts** | | |
| GET | `/api/v1/prompts` | List all prompt versions |
| POST | `/api/v1/prompts` | Create prompt version |
| GET | `/api/v1/prompts/{id}` | Get prompt version |
| PUT | `/api/v1/prompts/{id}` | Update prompt version |
| DELETE | `/api/v1/prompts/{id}` | Delete prompt version |
| POST | `/api/v1/prompts/{id}/activate` | Set as active |
| POST | `/api/v1/prompts/sync` | Sync from Agenta.ai |
| **Results** | | |
| GET | `/api/v1/results` | List results (with filters) |
| GET | `/api/v1/results/compare` | Compare results for an input |
| PUT | `/api/v1/results/{id}/override` | Manual correction |
| **Catalog** | | |
| GET | `/api/v1/catalog` | List catalog entries |
| GET | `/api/v1/catalog/{id}` | Get catalog entry |
| PUT | `/api/v1/catalog/{id}` | Update entry status |
| GET | `/api/v1/catalog/export` | Export CSV |
| **Models** | | |
| GET | `/api/v1/models` | List models + status |
| PUT | `/api/v1/models/{id}` | Update model config |
| **Evaluation** | | |
| POST | `/api/v1/eval/run` | Run evaluation against gold standard |
| GET | `/api/v1/eval/results` | Get evaluation results |

### 4.5 Configuration Files

| File | Purpose | Format |
|------|---------|--------|
| `ocrs.yaml` | OCR model configurations (models, parameters, endpoints) | YAML |
| `configs.toml` | Application configuration (paths, DB connection, API keys, OpenRouter settings) | TOML |
| `prompts/` | Local copies of prompt versions (synced from Agenta.ai) | Markdown |

### 4.6 Integration Points

| Integration | Direction | Protocol |
|-------------|-----------|----------|
| Agenta.ai | Bidirectional sync (prompts) | REST API |
| OpenRouter | Outbound (LLM post-processing) | REST API (OpenAI SDK compatible) |
| GLM OCR | Outbound (OCR requests, future) | REST API |
| Hugging Face | Inbound (model weights at startup) | HTTP download |
| X/Twitter | Inbound (image from post URL) | REST API / scraping |
| Facebook | Inbound (image from post URL) | REST API / scraping |
| PostgreSQL | Bidirectional (all data) | TCP (SQLAlchemy async) |

### 4.7 Security & Privacy

- API keys stored in `configs.toml` (excluded from git via `.gitignore`)
- No user authentication (single-operator, self-hosted)
- Social media images stored locally, not re-distributed
- HTTPS enforced on VPS deployment
- Database credentials managed via environment variables on VPS

### 4.8 Tech Stack Summary

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + TypeScript, Vite | Fast development, good ecosystem |
| Backend API | FastAPI (Python 3.12) | Async, OpenAPI auto-docs, Python ecosystem |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Industry standard, async support |
| Database | PostgreSQL 16 | JSONB for flexible model configs, relational for catalog |
| Task Queue | Dramatiq + Redis | Lightweight, reliable, supports retries |
| OCR Engine | Python (shared process or subprocess) | Direct model integration |
| LLM Provider | OpenRouter | Multi-model access via single API, configurable per prompt |
| Package Manager | uv | Fast, already in use |
| Linter | ruff | Already configured |
| Deployment | Docker Compose on single VPS | Simple, reproducible |

---

## 5. Risks & Roadmap

### 5.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| OCR accuracy on stylized manga text (handwritten, artistic fonts) | High — false negatives in catalog | Run multiple models in parallel; LLM post-processing to recover partial matches; manual review queue |
| Agenta.ai API downtime blocks prompt sync | Medium — cannot update prompts | Local prompt fallback; prompts/ directory serves as cache |
| OpenRouter API rate limits or cost | Medium — limits throughput | Configurable model selection; prompt optimization to reduce tokens |
| Social media platform API changes break image extraction | Medium — input pipeline breaks | URL-based image extraction with fallback scraping; manual upload as always-available alternative |
| Japanese text extraction quality varies by model | High — core functionality | Per-model confidence scoring; ensemble approach (majority vote across models) |
| VPS resource constraints with multiple OCR models | Medium — slow processing | Model loading/unloading; process only enabled models; batch processing |

### 5.2 Phased Roadmap

**Phase 0 — OCR Engine Module** (current phase)
- Standalone Python package: `manga_ocr/`
- manga-ocr + Tesseract wrappers with abstract model interface
- OpenRouter LLM post-processing via OpenAI SDK
- Rule-based matching (ISBN regex, title normalization)
- Pydantic schemas for all data types
- Config loading from `configs.toml` + `ocrs.yaml`
- Unit + integration tests
- Jupyter notebook for interactive testing

**Phase 1 — MVP (Core Pipeline)**
- Backend API with FastAPI + PostgreSQL + Alembic migrations
- Dramatiq + Redis task queue
- LLM post-processing with prompt loaded from config
- Manual image upload endpoint
- Basic results storage and retrieval API
- Frontend: minimal React app with upload form and results table

**Phase 2 — Multi-Model + Prompt Management**
- Add remaining OCR models (PaddleOCR, EasyOCR, GLM OCR)
- Agenta.ai integration for prompt versioning
- Prompt CRUD UI in frontend
- Pipeline visualization (static diagram)
- Social media URL input (X/Twitter, Facebook)

**Phase 3 — Evaluation & Comparison**
- Gold standard dataset management
- Results comparison viewer (side-by-side)
- Evaluation pipeline (regression testing on prompt changes)
- Manual correction / ground truth override
- Catalog management UI with search/filter/export

**Phase 4 — Polish & Production**
- Docker Compose deployment
- Real-time pipeline status (WebSocket)
- CSV export
- Error handling and retry logic
- Monitoring/logging
