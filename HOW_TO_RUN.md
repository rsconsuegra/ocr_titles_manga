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

### 2. Choose your PyTorch variant

The project supports two PyTorch backends, controlled by the `TORCH_VARIANT` env var:

| Variable | Backend | Image size | Use case |
|----------|---------|-----------|----------|
| `TORCH_VARIANT=cpu` | CPU-only (~2 GB) | Small | Local dev, macOS, machines without GPU |
| `TORCH_VARIANT=cuda` | CUDA 12.8 (~4 GB) | Large | Linux servers with NVIDIA GPU |

Set it in `.env`:

```bash
# For CPU (default)
TORCH_VARIANT=cpu

# For GPU
TORCH_VARIANT=cuda
```

### 3. Build and run

**CPU (macOS / no GPU):**

```bash
# Start Colima first (macOS only)
colima start

# Build and run
make dev-cpu
# or manually:
TORCH_VARIANT=cpu docker compose up --build
```

**GPU (Linux with NVIDIA):**

```bash
# Ensure NVIDIA Container Toolkit is installed
nvidia-ctk --version

# Build and run
make dev-gpu
# or manually:
TORCH_VARIANT=cuda docker compose up --build
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
| `TORCH_VARIANT` | `cpu` | PyTorch backend: `cpu` or `cuda` |

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
| `make dev-cpu` | Build + run all services with CPU PyTorch |
| `make dev-gpu` | Build + run all services with CUDA PyTorch |
| `make docker-build` | Build images (set `TORCH_VARIANT`) |
| `make docker-build-gpu` | Build images with CUDA |
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

The project uses uv's [optional dependencies](https://docs.astral.sh/uv/guides/integration/pytorch/) feature to support both CPU and CUDA PyTorch from a single lockfile.

**pyproject.toml** defines two conflicting extras:

```toml
[project.optional-dependencies]
cpu = ["torch>=2.9.1", "torchvision>=0.24.1"]
cuda = ["torch>=2.9.1", "torchvision>=0.24.1"]

[tool.uv.sources]
torch = [
  { index = "pytorch-cpu", extra = "cpu" },
  { index = "pytorch-cu128", extra = "cuda" },
]
```

**Dockerfile** accepts a build arg:

```dockerfile
ARG TORCH_VARIANT=cpu
RUN uv sync --frozen --no-dev --extra ${TORCH_VARIANT}
```

**docker-compose.yml** passes the env var:

```yaml
build:
  args:
    TORCH_VARIANT: ${TORCH_VARIANT:-cpu}
```

This means:
- A **single `uv.lock`** contains resolution data for both CPU and CUDA variants
- `uv sync --extra cpu` installs CPU-only torch (~200 MB)
- `uv sync --extra cuda` installs CUDA 12.8 torch (~2.5 GB with nvidia libs)
- Docker builds select the variant via the `TORCH_VARIANT` build argument

## Local Development (without Docker)

For day-to-day coding, you can run the backend locally and only use Docker for Postgres/Redis:

```bash
# Install deps
uv sync

# Start databases
make db-up
make migrate

# Run services in separate terminals
make api          # Terminal 1
make worker       # Terminal 2
make frontend     # Terminal 3
```

On macOS, `uv sync` installs CPU-only PyTorch from PyPI (no special configuration needed).

## Troubleshooting

### Docker build fails on macOS

Make sure Colima is running with enough resources:

```bash
colima start --cpu 4 --memory 8 --disk 60
```

### GPU not detected in container

Verify NVIDIA Container Toolkit:

```bash
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

### Port conflicts

If ports 5173, 8000, 5432, or 6379 are in use, edit `docker-compose.yml` to remap the host ports.

### Rebuilding after dependency changes

```bash
docker compose build --no-cache
```
