.PHONY: test lint run setup notebook db-up db-down migrate migrate-create clean worker api frontend setup-db typecheck security frontend-lint frontend-format dev stop

setup:
	uv sync

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check --config .code_quality/ruff.toml ocr_manga_title
	uv run ruff format --config .code_quality/ruff.toml --check ocr_manga_title

typecheck:
	uv run mypy --config-file .code_quality/mypy.ini ocr_manga_title/

security:
	uv run bandit -c .code_quality/bandit.yaml -r ocr_manga_title/

run:
	uv run python -m ocr_manga_title.cli

api:
	uv run uvicorn ocr_manga_title.api.app:create_app --factory --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

notebook:
	uv run jupyter notebook notebooks/

db-up:
	colima start 2>/dev/null || true
	docker compose -f docker-compose.dev.yml up -d
	@echo "Waiting for databases..."
	@sleep 3

db-down:
	docker compose -f docker-compose.dev.yml down

migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-create:
	uv run alembic revision --autogenerate -m "$(msg)"

setup-db: db-up migrate

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +

worker:
	uv run dramatiq ocr_manga_title.workers.ocr_worker

frontend-lint:
	cd frontend && npm run lint

frontend-format:
	cd frontend && npm run format:check

dev:
	colima start 2>/dev/null || true
	docker compose up --build

stop:
	docker compose -f docker-compose.dev.yml stop
	docker compose stop
