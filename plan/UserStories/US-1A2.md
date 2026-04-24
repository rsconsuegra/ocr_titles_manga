# US-1A2: Seed Model Configurations

**Sub-phase**: 1A — Database Layer
**Depends on**: US-1A1 (tables must exist)
**Blocks**: US-1B7 (model config routes), US-1C1 (worker reads model configs)

---

## Overview

Create Alembic seed migration that populates `model_configs` with the 4 OCR models matching the existing `ocrs.yaml` defaults. This ensures the system has model configuration out of the box after running migrations.

---

## Implementation Details

### 1. `migrations/versions/002_seed_models.py`

Alembic migration that inserts 4 rows into `model_configs`:

```python
def upgrade() -> None:
    op.bulk_insert(
        sa.table(
            "model_configs",
            sa.column("id", sa.String),
            sa.column("model_name", sa.String),
            sa.column("is_enabled", sa.Boolean),
            sa.column("parameters", sa.JSON),
            sa.column("language_hint", sa.String),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "id": str(uuid.uuid4()),
                "model_name": "tesseract",
                "is_enabled": True,
                "parameters": {
                    "languages": ["eng", "jpn"],
                    "psm": 3,
                    "oem": 3,
                },
                "language_hint": "eng+jpn",
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": str(uuid.uuid4()),
                "model_name": "paddle",
                "is_enabled": False,
                "parameters": {"languages": ["en", "ja"]},
                "language_hint": "en+ja",
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": str(uuid.uuid4()),
                "model_name": "easyocr",
                "is_enabled": False,
                "parameters": {"languages": ["en", "ja"]},
                "language_hint": "en+ja",
                "updated_at": datetime.now(timezone.utc),
            },
            {
                "id": str(uuid.uuid4()),
                "model_name": "glm_ocr",
                "is_enabled": False,
                "parameters": {"api_endpoint": ""},
                "language_hint": None,
                "updated_at": datetime.now(timezone.utc),
            },
        ],
    )

def downgrade() -> None:
    op.execute("DELETE FROM model_configs WHERE model_name IN ('tesseract', 'paddle', 'easyocr', 'glm_ocr')")
```

**Parameter values match `ocrs.yaml`** (read the existing config to verify):
- tesseract: `languages: ["eng", "jpn"]`, `psm: 3`, `oem: 3`, enabled
- paddle: `languages: ["en", "ja"]`, disabled
- easyocr: `languages: ["en", "ja"]`, disabled
- glm_ocr: `api_endpoint: ""`, disabled

---

## Acceptance Criteria

- [ ] `alembic upgrade head` inserts exactly 4 rows into `model_configs`
- [ ] Tesseract is enabled, other 3 are disabled
- [ ] `model_name` values match `ocr_manga_title/config.py` `KNOWN_MODELS = {"tesseract", "paddle", "easyocr", "glm_ocr"}`
- [ ] `downgrade()` removes the seeded rows
- [ ] Running migration on an already-seeded DB is safe (use `bulk_insert` which is idempotent or add `WHERE NOT EXISTS` guard)

---

## Test Specifications

**File**: `tests/test_db/test_crud.py` (partial — model config CRUD)

Tests:
- After migration, `SELECT COUNT(*) FROM model_configs` returns 4
- `SELECT * FROM model_configs WHERE model_name='tesseract'` returns row with `is_enabled=True`
- `SELECT * FROM model_configs WHERE is_enabled=True` returns exactly 1 row (tesseract)
- Each model_name is unique (unique constraint verified)
