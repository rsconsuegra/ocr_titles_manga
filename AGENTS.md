# AGENTS.md

Project instructions for AI coding agents working on manga_ocr.

## Project Overview

Manga OCR is a full-stack application for extracting and translating text from manga images. It combines multiple OCR engines (PaddleOCR, EasyOCR, Tesseract) with LLM-powered post-processing via OpenRouter.

**Stack:**
- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, Redis, Dramatiq (task queue)
- **Frontend:** React 19, TypeScript, Vite 6, Tailwind CSS v4
- **OCR engines:** PaddleOCR, EasyOCR, Tesseract (PyTorch-backed)
- **Package manager:** uv (Python), npm (frontend)

## Domain Context

This application extracts manga metadata from social media screenshots
(Facebook, Twitter/X, Reddit). The content is typically:

- **Popular manga/manhwa/manhua titles** being discussed in community posts
- **Doujinshi** published on nhentai, identified by a 6-digit gallery code

The `code` field in the extraction schema refers to this 6-digit nhentai
gallery identifier (e.g., `177013`). Not all images will contain a code.
The community often refers to this as "sauce" or "source".

When designing prompts, aliases, or parsing logic, assume this context.

## Commands

### Development

| Command | Description |
|---------|-------------|
| `make setup` | Install Python deps (`uv sync --extra cpu --group dev`) |
| `make api` | Start FastAPI dev server on `:8000` |
| `make frontend` | Start Vite dev server on `:5173` |
| `make worker` | Start Dramatiq OCR worker |
| `make db-up` | Start Postgres + Redis in Docker |
| `make db-down` | Stop Postgres + Redis |
| `make setup-db` | `db-up` + run migrations |
| `make migrate` | Run Alembic migrations |
| `make migrate-create msg="desc"` | Create new migration |

### Code Quality

| Command | Description |
|---------|-------------|
| `make test` | Run pytest (`uv run --extra cpu pytest tests/ -v`) |
| `make lint` | Run ruff lint + format check (backend) |
| `make typecheck` | Run mypy (backend) |
| `make security` | Run bandit (backend) |
| `make frontend-lint` | Run eslint (frontend) |
| `make frontend-format` | Run prettier check (frontend) |

### Docker

| Command | Description |
|---------|-------------|
| `make dev-cpu` | Build + run full stack (CPU) |
| `make dev-gpu` | Build + run full stack (CUDA 12.6) |
| `make docker-down` | Stop all services |

## Architecture

```
Frontend (:5173)  →  /api  →  FastAPI (:8000)  →  PostgreSQL (:5432)
                                       ↕
                                  Dramatiq Worker  →  Redis (:6379)
                                       ↕
                                  OCR Engines + OpenRouter LLM
```

- Frontend proxies `/api` to the backend via Vite's dev server config
- Backend is async throughout (asyncpg, async SQLAlchemy, async FastAPI)
- OCR processing is offloaded to Dramatiq workers (Redis-backed task queue)
- LLM post-processing uses OpenRouter API

### Directory Structure

```
ocr_manga_title/          # Python backend package
  api/                    # FastAPI routes and app factory
  db/                     # SQLAlchemy models and database layer
  engine/                 # OCR engine implementations
  postprocess/            # LLM post-processing logic
  preprocess/             # Image preprocessing pipelines
  services/               # Business logic layer
  workers/                # Dramatiq task definitions
  config.py, settings.py  # Configuration and env loading

frontend/src/             # React frontend
  api/                    # API client functions
  components/             # Reusable UI components
  pages/                  # Page-level components
  hooks/                  # Custom React hooks
  utils/                  # Utility functions

migrations/               # Alembic database migrations
tests/                    # pytest test suite
scripts/                  # Utility scripts (screenshot, etc.)
```

## Code Conventions

### Python (Backend)

- **Formatter/Linter:** ruff (config at `.code_quality/ruff.toml`)
- **Type checking:** mypy (config at `.code_quality/mypy.ini`)
- **Security:** bandit (config at `.code_quality/bandit.yaml`)
- **Style:** Follow Google Python Style Guide, PEP 8
- **Async:** Use `async/await` throughout — all DB and I/O operations are async
- **Pydantic v2:** Use `model_config = ConfigDict(...)` style, not `class Config`
- **Tests:** pytest with `pytest-asyncio` (auto mode), test files in `tests/`
- Run `make lint`, `make typecheck` after backend changes

### TypeScript/React (Frontend)

- **Formatter:** prettier (config at `frontend/.prettierrc`)
- **Linter:** eslint with react, jsx-a11y, hooks plugins
- **Imports:** `simple-import-sort` plugin enforces import ordering
- **Components:** Functional components with hooks
- **Styling:** Tailwind CSS v4 (via `@tailwindcss/vite` plugin)
- Run `make frontend-lint`, `make frontend-format` after frontend changes

### General

- No emojis in code or commit messages unless explicitly requested
- No comments unless explicitly requested
- Do not commit `.env` or secrets
- `uploads/` directory is gitignored — use for temporary files, screenshots, etc.

## Vision-Driven UI Design Workflow

This project has Playwright installed for automated screenshot capture, enabling a visual feedback loop with the Z.AI Vision MCP.

### Prerequisites

1. Frontend dev server running: `make frontend`
2. Playwright + Chromium installed in `frontend/` (already set up)

### Taking a Screenshot

```bash
make screenshot
```

This runs `scripts/screenshot.mjs` which:
- Launches headless Chromium (1280x720 viewport)
- Navigates to `http://localhost:5173`
- Waits for `networkidle` (API calls, lazy loads finish)
- Saves to `uploads/screenshot.png`

**Custom URL or output path:**

```bash
NODE_PATH=./frontend/node_modules node scripts/screenshot.mjs \
  --url http://localhost:5173/settings \
  --output uploads/screenshot-settings.png
```

### The Agent Loop

When designing or iterating on UI:

1. **Edit** React components in `frontend/src/`
2. **Capture** with `make screenshot`
3. **Analyze** with `zai-vision_analyze_image` or `zai-vision_ui_to_artifact` on `uploads/screenshot.png`
4. **Iterate** based on visual feedback
5. **Repeat** until the UI matches the design intent

### Available Vision MCP Tools

| Tool | Use When |
|------|----------|
| `zai-vision_analyze_image` | General image analysis, fallback for other tools |
| `zai-vision_ui_to_artifact` | Generate frontend code from a UI screenshot |
| `zai-vision_extract_text_from_screenshot` | Extract visible text from screenshots |
| `zai-vision_diagnose_error_screenshot` | Analyze error screenshots from the browser |
| `zai-vision_ui_diff_check` | Compare expected vs actual UI screenshots |

### Tips

- The screenshot captures the current state of whatever is at `localhost:5173`
- For page-specific screenshots, navigate to the route first (e.g., `--url http://localhost:5173/manga/123`)
- If the dev server is not running, `make screenshot` will fail with a connection error
- Screenshots are saved to `uploads/` which is gitignored — they won't pollute the repo
