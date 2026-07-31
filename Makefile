BUILDER = manga-ocr
GPU_COMPOSE = -f docker-compose.yml -f docker-compose.gpu.yml
DB_SERVICES = postgres redis

.PHONY: test lint run setup notebook db-up db-down migrate migrate-down migrate-create clean worker api frontend setup-db typecheck security frontend-lint frontend-format screenshot dev dev-cpu dev-gpu stop docker-build docker-build-gpu docker-up docker-down reset ensure-builder

setup:
	uv sync --extra cpu --group dev

test:
	uv run --extra cpu pytest tests/ -v

lint:
	uv run --extra cpu ruff check --config .code_quality/ruff.toml ocr_manga_title
	uv run --extra cpu ruff format --config .code_quality/ruff.toml --check ocr_manga_title

typecheck:
	uv run --extra cpu mypy --config-file .code_quality/mypy.ini ocr_manga_title/

security:
	uv run --extra cpu bandit -c .code_quality/bandit.yaml -r ocr_manga_title/

run:
	uv run --extra cpu python -m ocr_manga_title.cli

api:
	uv run --extra cpu uvicorn ocr_manga_title.api.app:create_app --factory --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

notebook:
	uv run --extra cpu jupyter notebook notebooks/

db-up:
	colima start 2>/dev/null || true
	docker compose up -d $(DB_SERVICES)
	@echo "Waiting for databases..."
	@sleep 3

db-down:
	docker compose rm -fs $(DB_SERVICES)

migrate:
	uv run --extra cpu alembic upgrade head

migrate-down:
	uv run --extra cpu alembic downgrade -1

migrate-create:
	uv run --extra cpu alembic revision --autogenerate -m "$(msg)"

setup-db: db-up migrate

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +

reset:
	docker compose down -v
	rm -rf ./uploads
	@echo "Reset complete. Run 'make dev' to start fresh."

worker:
	uv run --extra cpu dramatiq ocr_manga_title.workers.ocr_worker

frontend-lint:
	cd frontend && npm run lint

frontend-format:
	cd frontend && npm run format:check

screenshot:
	NODE_PATH=./frontend/node_modules node scripts/screenshot.mjs

ensure-builder:
	@docker buildx inspect $(BUILDER) >/dev/null 2>&1 || \
		docker buildx create --name $(BUILDER) --driver docker-container --use
	@docker buildx use $(BUILDER) 2>/dev/null || true

dev: dev-cpu

dev-cpu: ensure-builder
	colima start 2>/dev/null || true
	OCR_EXTRA=cpu docker compose up --build

dev-gpu: ensure-builder
	OCR_EXTRA=cu126 docker compose $(GPU_COMPOSE) up --build

docker-build: ensure-builder
	OCR_EXTRA=$${OCR_EXTRA:-cpu} docker compose build

docker-build-gpu: ensure-builder
	OCR_EXTRA=cu126 docker compose $(GPU_COMPOSE) build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

stop:
	docker compose stop
