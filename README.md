# Manga OCR Title

A full-stack application that extracts manga titles from cover images using multi-engine OCR, LLM-based extraction, and rule-based matching. Built with a FastAPI backend, React frontend, and Dramatiq/Redis async workers, all orchestrated via Docker Compose.

## Features

- **Multi-engine OCR** -- Tesseract, PaddleOCR, EasyOCR, and Vision API (GLM OCR), all production-ready
- **Multilingual support** -- English, Japanese, Chinese, Korean, Spanish, French, German, Portuguese, Italian
- **Image preprocessing pipeline** -- ROI detection, grayscale, upscale, denoise, binarize with configurable parameters
- **LLM title extraction** -- OpenRouter API with rule-based ISBN matching fallback
- **Content-addressable image cache** -- Avoids redundant preprocessing and OCR operations
- **Pipeline profiles** -- Named, reusable configurations with immutable snapshots per run
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
make dev

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
| Backend      | Python 3.12, FastAPI, SQLAlchemy (async), Alembic, Dramatiq             |
| OCR          | PyTesseract, PaddleOCR, EasyOCR, OpenAI client                          |
| Frontend     | React 19, TypeScript 5, Vite 6, Tailwind CSS 4, React Router 7         |
| Database     | PostgreSQL 18                                                           |
| Message Queue| Redis 8                                                                 |
| Testing      | pytest, pytest-asyncio, httpx AsyncClient, SQLite in-memory (356 tests) |
| Infrastructure| Docker Compose, Colima                                                 |

## Project Structure

```
manga_ocr/
├── ocr_manga_title/     # Backend application
│   ├── api/             # FastAPI routes and app factory
│   ├── db/              # SQLAlchemy models and sessions
│   ├── engine/          # OCR engine adapters
│   ├── postprocess/     # Title extraction and ISBN matching
│   ├── preprocess/      # Image preprocessing pipeline
│   ├── services/        # Business logic layer
│   └── workers/         # Dramatiq task definitions
├── frontend/            # React SPA
├── config/              # OCR, preprocessing, and app configs
├── migrations/          # Alembic database migrations
├── tests/               # Test suite
└── docker-compose.yml   # Service orchestration
```

## Configuration

| File              | Purpose                                         |
|-------------------|-------------------------------------------------|
| `.env`            | Database URL, Redis URL, API keys, CORS origins |
| `config/ocrs.yaml`| OCR engine definitions and default parameters   |
| `config/preprocess.yaml` | Preprocessing step defaults                |
| `config/configs.toml`    | Application-level settings                |

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

## Make Commands

| Command              | Description                                |
|----------------------|--------------------------------------------|
| `make dev`           | Build and start all services via Docker    |
| `make dev-gpu`       | Same as above with CUDA support            |
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
