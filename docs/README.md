# Manga OCR Title — Documentation

## Table of Contents

1. **[Architecture](architecture.md)** — System overview, processing pipelines, component map, exception hierarchy, key design decisions

2. **[Backend Reference](backend.md)** — Module index, OCR engine, preprocessing pipeline, post-processing (LLM + rules), services layer, settings, worker, CLI

3. **[Database Reference](database.md)** — Schema diagram, all 10 ORM models with column details, ~30 CRUD functions, migration chain, session management

4. **[API Reference](api-reference.md)** — All 48 endpoints across 13 route modules, request/response schemas, error responses, OpenAPI/Swagger info

5. **[Frontend Reference](frontend.md)** — React app structure, routing, API client, components, hooks, key pages (Upload, QuickRun, RunDetail, BatchDetail, ProfileEditor)

6. **[Infrastructure & Deployment](infrastructure.md)** — Docker Compose stack, Dockerfile, Makefile commands, local dev setup, environment variables, config files, dependencies

7. **[Configuration System](configuration.md)** — Config sources, loading functions, pipeline profiles, snapshot mechanism, config scope matrix

8. **[Testing](testing.md)** — Test structure, fixtures, running tests, test patterns, code quality commands

---

## Quick Start

```bash
# Install deps
make setup

# Start infrastructure (PostgreSQL + Redis)
make db-up

# Run migrations
make migrate

# Start API
make api

# Start worker (separate terminal)
make worker

# Start frontend (separate terminal)
make frontend
```

Then open:
- **Frontend**: http://localhost:5173
- **API Docs (Swagger)**: http://localhost:8000/api/docs
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json
