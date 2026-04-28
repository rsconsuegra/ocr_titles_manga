# Infrastructure & Deployment

## Docker Compose

### Production Stack (`docker-compose.yml`)

6 services:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | `postgres:18-alpine` | 5432 | Primary database |
| `redis` | `redis:8-alpine` | 6379 | Dramatiq message broker |
| `migrate` | Built from Dockerfile | — | Runs `alembic upgrade head` on startup |
| `api` | Built from Dockerfile | 8000 | FastAPI application |
| `worker` | Built from Dockerfile | — | Dramatiq worker |
| `frontend` | Built from `frontend/Dockerfile` | 5173:80 | Nginx (production) |

**Startup order**: postgres → migrate (completes) → api + worker (depend on migrate + redis) → frontend (depends on api)

**Shared volumes**:
- `./uploads:/app/uploads` (api + worker share uploaded images)
- `ocr_cache:/app/cache` (api + worker share image cache)
- `pgdata:/var/lib/postgresql` (postgres data)

For local dev, run `make db-up` for PostgreSQL + Redis only.

---

## Dockerfile

```dockerfile
ARG OCR_EXTRA=cpu

FROM python:3.12-slim

# Install Tesseract + 9 language packs + ccache
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-chi-sim \
    tesseract-ocr-kor tesseract-ocr-spa tesseract-ocr-fra tesseract-ocr-deu \
    tesseract-ocr-por tesseract-ocr-ita ccache && rm -rf /var/lib/apt/lists/*

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --extra ${OCR_EXTRA}
COPY . .

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "ocr_manga_title.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

The `OCR_EXTRA` build arg controls which OCR dependency set is installed (`cpu` or `cu126`).

---

## Makefile Commands

| Command | Description |
|---|---|
| `make setup` | Install Python dependencies via uv |
| `make api` | Start FastAPI dev server on :8000 |
| `make worker` | Start Dramatiq worker |
| `make frontend` | Start Vite dev server on :5173 |
| `make dev` | Start full Docker Compose stack |
| `make stop` | Stop all containers |
| `make db-up` | Start PostgreSQL + Redis containers |
| `make db-down` | Stop PostgreSQL + Redis containers |
| `make migrate` | Run `alembic upgrade head` |
| `make migrate-down` | Rollback one migration |
| `make migrate-create msg="..."` | Create new autogenerate migration |
| `make setup-db` | `db-up` + `migrate` |
| `make test` | Run pytest |
| `make lint` | Run ruff check + format check |
| `make typecheck` | Run mypy |
| `make security` | Run bandit |
| `make frontend-lint` | Run frontend ESLint |
| `make frontend-format` | Run frontend Prettier check |
| `make clean` | Remove `__pycache__` directories |

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js (for frontend)
- Docker + Colima (or Docker Desktop) for PostgreSQL + Redis
- Tesseract OCR (for local OCR processing)

### Steps

```bash
# 1. Install Python deps
make setup

# 2. Start infrastructure
make db-up

# 3. Run migrations
make migrate

# 4. Start API (terminal 1)
make api

# 5. Start worker (terminal 2)
make worker

# 6. Start frontend (terminal 3)
make frontend

# 7. Open browser
# API docs: http://localhost:8000/api/docs
# Frontend: http://localhost:5173
```

### Full Docker Compose

```bash
make dev
```

This starts all 6 services via Docker Compose.

---

## Environment Variables

All env vars have sensible defaults for local development. Override as needed:

| Variable | Default | Used By |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://manga_ocr:manga_ocr_dev@localhost:5432/manga_ocr` | API, worker, migrations |
| `REDIS_URL` | `redis://localhost:6379` | Worker |
| `DB_POOL_SIZE` | `5` | API |
| `DB_MAX_OVERFLOW` | `10` | API |
| `DB_POOL_TIMEOUT` | `30` | API |
| `DB_WORKER_POOL_SIZE` | `2` | Worker |
| `DB_WORKER_MAX_OVERFLOW` | `0` | Worker |
| `OCR_EXTRA` | `cpu` | Docker build arg for OCR dependency set |

---

## Configuration Files

Three config files in `config/`:

### `config/configs.toml`

Application-level config (loaded once, cached via `lru_cache`):

```toml
images_path = "/path/to/images"

[openrouter]
api_key = "sk-or-replace-me"
default_model = "google/gemini-2.5-flash"
base_url = "https://openrouter.ai/api/v1"
```

- `images_path`: Directory for debug preprocessing output
- `openrouter.api_key`: OpenRouter API key (must start with `sk-`)
- `openrouter.default_model`: LLM model for title extraction
- `openrouter.base_url`: OpenAI-compatible API endpoint

### `config/ocrs.yaml`

OCR model definitions (used only as seed data; runtime config comes from DB `model_configs` table):

```yaml
models:
  tesseract:
    enabled: true
    languages: ["eng", "jpn"]
    psm: 3
    oem: 3
  paddle:
    enabled: false
    languages: ["en", "ja"]
  # ...
```

### `config/preprocess.yaml`

Preprocessing pipeline config (loaded by worker when no profile snapshot exists):

```yaml
preprocessing:
  enabled: true
  debug: true
  roi:
    enabled: true
    method: "contour"
    min_area: 500
    padding: 10
    merge_overlap: 0.3
  grayscale:
    enabled: true
  upscale:
    enabled: true
    method: "cubic"
    scale_factor: 2
  denoise:
    enabled: true
    method: "gaussian"
    strength: "light"
  binarize:
    enabled: true
    method: "otsu"
    invert: false
    block_size: 11
    c: 2
```

---

## Python Dependencies

### Production (`pyproject.toml`)

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `sqlalchemy[asyncio]` | ORM + async support |
| `asyncpg` | PostgreSQL async driver |
| `alembic` | Database migrations |
| `pydantic` | Data validation |
| `dramatiq[redis]` | Task queue |
| `pytesseract` | Tesseract Python binding |
| `opencv-python-headless` | Image processing |
| `numpy` | Array operations |
| `pillow` | Image I/O |
| `openai` | OpenAI-compatible API client |
| `pyyaml` | YAML config parsing |
| `python-multipart` | File upload handling |
| `paddlepaddle` | PaddleOCR inference engine |
| `paddleocr` | PaddleOCR Python binding |
| `easyocr` | EasyOCR Python binding |
| `torch` | PyTorch (EasyOCR dependency) |

### Development

| Package | Purpose |
|---|---|
| `pytest` + `pytest-asyncio` | Async test runner |
| `httpx` | Async HTTP test client |
| `aiosqlite` | SQLite async driver (tests) |
| `ruff` | Linter + formatter |
| `mypy` | Type checker |
| `bandit` | Security scanner |
| `pytest-cov` | Coverage reporting |

---

## Frontend Dockerfile

Multi-stage build using `node:24-slim` for the build stage. Production image uses nginx to serve static assets with `client_max_body_size 50m` configured for large image uploads. Port 80 inside the container is mapped to 5173 on the host.

---

## Alembic Configuration

- Config file: `alembic.ini`
- Migrations dir: `migrations/`
- Models imported from: `ocr_manga_title.db.models.Base`
- URL sourced from: `settings.DATABASE_URL` (set at runtime in `migrations/env.py`)
- Async engine used for online migrations
