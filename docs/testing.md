# Testing

## Overview

- **Framework**: pytest + pytest-asyncio
- **Database**: SQLite in-memory (overridden via fixtures)
- **HTTP Client**: httpx AsyncClient
- **356 tests** across 15 test files

---

## Test Configuration

Defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

All async tests run automatically without explicit `@pytest.mark.asyncio`.

---

## Directory Structure

```
tests/
├── conftest.py                     # Shared fixtures (db_engine, db_session, blank_image_bytes)
├── test_api/
│   ├── conftest.py                 # API test fixtures (client, monkeypatched dirs)
│   ├── test_batches.py             # Batch endpoint tests (11 tests)
│   ├── test_catalog.py             # Catalog endpoint tests
│   ├── test_inputs.py              # Upload endpoint tests
│   ├── test_models_route.py        # Model config endpoint tests
│   ├── test_ocr_playground.py      # OCR playground tests
│   ├── test_pipeline.py            # Pipeline trigger/list/cancel tests (16 tests)
│   ├── test_preprocess.py          # Preprocessing playground tests
│   ├── test_quick_run.py           # Quick run endpoint tests
│   └── test_results.py             # Results endpoint tests
├── test_batch_progress.py          # Batch progress CRUD logic (5 tests)
├── test_cli.py                     # CLI runner tests
├── test_config.py                  # Config loading + validation tests
├── test_db/                        # ORM and CRUD tests
├── test_engine/                    # OCREngine and model adapter tests
├── test_postprocess.py             # LLMExtractor + RuleMatcher tests
├── test_cache.py                   # Image cache service tests (12 tests)
├──_preprocess.py                   # Preprocessing step tests
├── test_schemas.py                 # Pydantic schema validation tests
└── test_worker/                    # Dramatiq worker tests
```

---

## Shared Fixtures (`conftest.py`)

### Database Fixtures

```python
@pytest.fixture
async def db_engine():
    """SQLite in-memory async engine for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """Async session with auto-rollback."""
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
```

### Test Data Fixtures

```python
@pytest.fixture
def blank_image_bytes():
    """Minimal valid PNG bytes (1x1 white pixel)."""
    ...
```

---

## API Test Fixtures (`test_api/conftest.py`)

```python
@pytest.fixture
async def client(db_engine, db_session):
    """httpx AsyncClient wired to the FastAPI app with test DB injection."""
    async def override_get_db():
        yield db_session

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

Also monkeypatches `UPLOAD_DIR` to a temp directory for upload tests, and patches `batches_module.UPLOAD_DIR`.

---

## Running Tests

```bash
# All tests
make test
# or
uv run pytest tests/ -v

# Specific file
uv run pytest tests/test_api/test_batches.py -v

# Specific test
uv run pytest tests/test_postprocess.py::test_rule_matcher_isbn13 -v

# With coverage
uv run pytest tests/ --cov=ocr_manga_title --cov-report=html
```

---

## Test Patterns

### Testing API Endpoints

```python
async def test_create_batch(client, blank_image_bytes):
    response = await client.post(
        "/api/v1/batches",
        files={"files": ("test.png", blank_image_bytes, "image/png")},
        data={"name": "Test Batch"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Batch"
    assert data["total_count"] == 1
```

### Testing CRUD Functions

```python
async def test_update_batch_progress(db_session):
    batch = await create_batch_run(db_session, name="test", total_count=2)
    # ... create pipeline runs with completed/failed status
    updated = await update_batch_progress(db_session, batch.id)
    assert updated.completed_count == 1
    assert updated.failed_count == 1
    assert updated.status == "partial_failure"
```

### Testing Worker Logic

Worker tests mock the `_run_async` helper or test `_process()` directly with a test session factory. The Dramatiq actor itself is tested by verifying the message is enqueued correctly.

### Mocking External Services

- **LLM calls**: Mocked via `unittest.mock.patch` on `openai.OpenAI.chat.completions.create`
- **Tesseract**: Tests use blank images; Tesseract is expected to be installed
- **Model availability**: `check_model_availability()` is often mocked to return True/False

### Testing Cache Operations

Cache tests mock the database session and verify hash computation, cache lookup, and TTL-based expiration. The cache module uses PostgreSQL-specific `INSERT ... ON CONFLICT` so SQLite is NOT supported for cache tests — mock the session instead.

---

## Code Quality Commands

```bash
# Lint (ruff)
make lint

# Type check (mypy)
make typecheck

# Security scan (bandit)
make security

# Frontend lint
make frontend-lint

# Frontend format check
make frontend-format
```
