# Manga OCR Title

A full-stack application that extracts manga titles from cover images using multi-engine OCR, LLM-based extraction, and rule-based matching. Built with a FastAPI backend, React frontend, and Dramatiq/Redis async workers, all orchestrated via Docker Compose.

## Features

- **Multi-engine OCR** -- Tesseract, PaddleOCR, EasyOCR, Ollama Vision OCR, and Vision API (GLM OCR), all production-ready
- **Multilingual support** -- English, Japanese, Chinese, Korean, Spanish, French, German, Portuguese, Italian
- **Image preprocessing pipeline** -- ROI detection, grayscale, upscale, denoise, binarize with configurable parameters
- **LLM title extraction** -- OpenRouter API with rule-based ISBN matching fallback
- **LLM provider switching** -- OpenRouter + Ollama with per-model JSON mode control
- **Encrypted credential storage** -- API keys stored with Fernet encryption
- **Settings UI** -- Manage API keys and Ollama configuration from the frontend
- **Content-addressable image cache** -- Avoids redundant preprocessing and OCR operations
- **Pipeline profiles** -- Named, reusable configurations with immutable snapshots per run
- **Profile import/export** -- Export and import profiles with validation
- **Cancel and retry** -- Cooperative cancellation for running jobs; retry for completed, failed, or cancelled runs
- **Batch processing** -- Upload multiple images, trigger all at once, track aggregate progress
- **Playground UIs** -- Interactive pages for preprocessing and OCR testing

## Architecture

```
┌────────────┐     ┌────────────┐     ┌───────────┐
│  React SPA │────▶│  FastAPI   │────▶│ PostgreSQL│
│  :5173     │◀────│  :8000     │     └───────────┘
└────────────┘     └─────┬──────┘
                         │ enqueue
                         ▼
                  ┌─────────────┐     ┌───────┐
                  │  Dramatiq   │────▶│ Redis │
                  │  Worker     │     └───────┘
                  └─────────────┘
```

## Quick Start

**Prerequisites:** Docker, Colima (macOS), `make`

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env and set OPENROUTER_API_KEY

# 2. Build and launch all services
make dev-cpu

# 3. Open the application
open http://localhost:5173
```

API documentation is available at http://localhost:8000/api/docs

## Local Development

Run services individually for live-reload workflows:

```bash
# Start infrastructure only
make setup-db

# Backend API (hot reload)
make api

# Background worker
make worker

# Frontend dev server (hot module reload)
make frontend
```

## Tech Stack

| Layer        | Technology                                                              |
|--------------|-------------------------------------------------------------------------|
| Backend      | Python 3.12, FastAPI, SQLAlchemy (async), Alembic, Dramatiq, cryptography |
| OCR          | PyTesseract, PaddleOCR, EasyOCR, Ollama Vision, OpenAI client          |
| Frontend     | React 19, TypeScript 5, Vite 6, Tailwind CSS 4, React Router 7         |
| Database     | PostgreSQL 18                                                           |
| Message Queue| Redis 8                                                                 |
| Testing      | pytest, pytest-asyncio, httpx AsyncClient, SQLite in-memory (374 tests) |
| Infrastructure| Docker Compose, Colima                                                 |

## Project Structure

```
manga_ocr/
├── ocr_manga_title/     # Backend application
│   ├── api/
│   │   └── routes/
│   │       ├── config/      # Settings, Ollama, LLM, profiles, catalog
│   │       ├── pipeline/    # Runs, batches, inputs, results
│   │       └── ocr/         # OCR, preprocessing, models
│   ├── db/                  # SQLAlchemy models and sessions
│   ├── engine/
│   │   ├── ollama_vision_model.py  # Ollama Vision OCR adapter
│   │   └── ...                     # Other OCR engine adapters
│   ├── postprocess/         # Title extraction and ISBN matching
│   ├── preprocess/          # Image preprocessing pipeline
│   ├── services/
│   │   ├── ollama.py            # Ollama provider logic
│   │   ├── credentials.py       # Encrypted credential storage
│   │   ├── config_live.py       # Live configuration management
│   │   ├── profile_import.py    # Profile import/export with validation
│   │   ├── warmup.py            # Worker warmup routines
│   │   └── ...                  # Other services
│   └── workers/             # Dramatiq task definitions
├── frontend/                # React SPA
├── config/
│   ├── llm_models.yaml      # LLM model definitions with JSON mode support flags
│   ├── ocrs.yaml             # OCR engine definitions and default parameters
│   ├── preprocess.yaml       # Preprocessing step defaults
│   └── configs.toml          # Application-level settings
├── migrations/              # Alembic database migrations
├── tests/                   # Test suite
└── docker-compose.yml       # Service orchestration
```

## Configuration

| File              | Purpose                                         |
|-------------------|-------------------------------------------------|
| `.env`            | Database URL, Redis URL, API keys, CORS origins |
| `config/ocrs.yaml`| OCR engine definitions and default parameters   |
| `config/preprocess.yaml` | Preprocessing step defaults                |
| `config/configs.toml`    | Application-level settings                |
| `config/llm_models.yaml` | LLM model definitions with JSON mode support flags |

Most settings can also be overridden per request through the API or pipeline profiles stored in the database.

## Testing

```bash
make test
```

Tests use SQLite in-memory databases via httpx `AsyncClient` for full isolation. No external services required.

## OCR Models

| Engine      | Class          | Languages                        | Key Parameters              |
|-------------|----------------|----------------------------------|-----------------------------|
| Tesseract   | `TesseractModel` | en, ja, ch, ko, es, fr, de, pt, it | `psm`, `oem`, `languages`  |
| PaddleOCR   | `PaddleModel`  | en, ja, ch, ko, es, fr, de, pt, it | `use_angle_cls`, `lang`    |
| EasyOCR     | `EasyOCRModel` | en, ja, ch, ko, es, fr, de, pt, it | `languages`, `gpu`         |
| Vision API  | `GLMOCRModel`  | All (model-dependent)            | `model`, `base_url`        |
| Ollama Vision | `OllamaVisionModel` | All (model-dependent)        | `model`, `base_url`        |

## Make Commands

| Command              | Description                                |
|----------------------|--------------------------------------------|
| `make dev-cpu`       | Build and start all services via Docker (CPU) |
| `make dev-gpu`       | Build and start all services via Docker (CUDA 12.6) |
| `make stop`          | Stop all containers                        |
| `make api`           | Run API server locally (hot reload)        |
| `make worker`        | Run Dramatiq worker locally                |
| `make frontend`      | Run frontend dev server                    |
| `make test`          | Run test suite                             |
| `make lint`          | Lint backend code (ruff)                   |
| `make typecheck`     | Type-check backend (mypy)                  |
| `make security`      | Security audit (bandit)                    |
| `make migrate`       | Apply pending Alembic migrations           |
| `make migrate-create`| Generate a new migration (`msg=` required) |
| `make reset`         | Remove all data and volumes                |

## License

[Add license here]
