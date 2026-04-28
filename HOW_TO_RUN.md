# How to Run

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2+
- (macOS) [Colima](https://github.com/abiosoft/colima) or Docker Desktop
- (GPU) [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

## Quick Start

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your `OPENROUTER_API_KEY`. Other defaults work out of the box.

### 2. Choose your OCR dependency set

The project supports two OCR dependency sets, controlled by the `OCR_EXTRA` env var:

| Variable | Backend | Use case |
|----------|---------|----------|
| `OCR_EXTRA=cpu` | CPU PaddlePaddle + CPU/PyPI PyTorch | Local dev, macOS, machines without GPU |
| `OCR_EXTRA=cu126` | PaddlePaddle GPU cu126 + PyTorch cu126 | Linux servers with NVIDIA GPU |

Set it in `.env`:

```bash
# For CPU (default)
OCR_EXTRA=cpu

# For GPU
OCR_EXTRA=cu126
```

### 3. Build and run

**CPU (macOS / no GPU):**

```bash
# Start Colima first (macOS only)
colima start

# Build and run
make dev-cpu
# or manually:
OCR_EXTRA=cpu docker compose up --build
```

**GPU (Linux with NVIDIA):**

```bash
# Ensure NVIDIA Container Toolkit is installed
nvidia-ctk --version

# Build and run
make dev-gpu
# or manually:
OCR_EXTRA=cu126 docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build
```

### 4. Access the app

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

## Architecture

```
                    ┌─────────────┐
                    │  Frontend   │ :5173 (nginx)
                    │  React+TS   │
                    └──────┬──────┘
                           │ /api
                    ┌──────┴──────┐
                    │     API     │ :8000 (uvicorn)
                    │   FastAPI   │
                    └──┬──────┬──┘
                 ┌─────┘      └─────┐
          ┌──────┴──────┐  ┌───────┴──────┐
          │   Worker    │  │   Postgres   │ :5432
          │  Dramatiq   │  │    18-alpine │
          └──────┬──────┘  └──────────────┘
                 │
          ┌──────┴──────┐
          │    Redis    │ :6379
          │   7-alpine  │
          └─────────────┘
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://manga_ocr:manga_ocr_dev@postgres:5432/manga_ocr` | PostgreSQL connection string |
| `REDIS_URL` | `redis://redis:6379` | Redis connection string |
| `OPENROUTER_API_KEY` | (required) | API key for LLM post-processing via OpenRouter |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost:3000"]` | Allowed CORS origins (JSON array) |
| `OCR_EXTRA` | `cpu` | OCR dependency set: `cpu` or `cu126` |

### PostgreSQL overrides (docker-compose.yml)

| Variable | Default |
|----------|---------|
| `POSTGRES_USER` | `manga_ocr` |
| `POSTGRES_PASSWORD` | `manga_ocr_dev` |
| `POSTGRES_DB` | `manga_ocr` |

## Makefile Targets

### Local Development (no Docker)

| Target | Description |
|--------|-------------|
| `make setup` | Install Python dependencies with uv |
| `make db-up` | Start Postgres + Redis in Docker |
| `make db-down` | Stop Postgres + Redis |
| `make setup-db` | `db-up` + run migrations |
| `make migrate` | Run Alembic migrations |
| `make migrate-create msg="desc"` | Create a new migration |
| `make api` | Start FastAPI dev server |
| `make worker` | Start Dramatiq worker |
| `make frontend` | Start React dev server |
| `make dev` | Build and run full stack in Docker (CPU) |

### Docker

| Target | Description |
|--------|-------------|
| `make dev-cpu` | Build + run all services with CPU OCR dependencies |
| `make dev-gpu` | Build + run all services with CUDA 12.6 OCR dependencies |
| `make docker-build` | Build images (set `OCR_EXTRA`) |
| `make docker-build-gpu` | Build GPU images with CUDA 12.6 |
| `make docker-up` | Start all services (detached) |
| `make docker-down` | Stop all services |

### Code Quality

| Target | Description |
|--------|-------------|
| `make test` | Run pytest |
| `make lint` | Run ruff lint + format check |
| `make typecheck` | Run mypy |
| `make security` | Run bandit |
| `make frontend-lint` | Lint frontend code |
| `make frontend-format` | Check frontend formatting |

## How CPU/CUDA Works

The project uses uv's optional dependencies to support CPU and CUDA OCR stacks from a single lockfile.

**pyproject.toml** defines two conflicting extras:

```toml
[project.optional-dependencies]
cpu = ["easyocr", "paddleocr", "paddlepaddle", "pytesseract", "torch", "torchvision"]
cu126 = ["easyocr", "paddleocr", "paddlepaddle-gpu", "pytesseract", "torch", "torchvision"]

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", extra = "cpu", marker = "sys_platform != 'darwin'" },
  { index = "pytorch-cu126", extra = "cu126", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

**Dockerfile** accepts a build arg:

```dockerfile
ARG OCR_EXTRA=cpu
RUN uv sync --frozen --no-dev --extra ${OCR_EXTRA}
```

**docker-compose.yml** passes the env var:

```yaml
build:
  args:
    OCR_EXTRA: ${OCR_EXTRA:-cpu}
```

This means:
- A **single `uv.lock`** contains resolution data for both CPU and CUDA variants
- `uv sync --extra cpu` installs the CPU OCR stack
- `uv sync --extra cu126` installs the CUDA 12.6 OCR stack on Linux
- Docker builds select the dependency set via the `OCR_EXTRA` build argument

## Local Development (without Docker)

For day-to-day coding, you can run the backend locally and only use Docker for Postgres/Redis:

```bash
# Install deps
uv sync --extra cpu --group dev

# Start databases
make db-up
make migrate

# Run services in separate terminals
make api          # Terminal 1
make worker       # Terminal 2
make frontend     # Terminal 3
```

On macOS, `uv sync --extra cpu --group dev` installs CPU PaddlePaddle and PyTorch from PyPI. CUDA is not available on macOS.

## Troubleshooting

### Docker build fails on macOS

Make sure Colima is running with enough resources:

```bash
colima start --cpu 4 --memory 8 --disk 60
```

### GPU not detected in container

Verify NVIDIA Container Toolkit:

```bash
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

### Port conflicts

If ports 5173, 8000, 5432, or 6379 are in use, edit `docker-compose.yml` to remap the host ports.

### Rebuilding after dependency changes

```bash
docker compose build --no-cache
```
