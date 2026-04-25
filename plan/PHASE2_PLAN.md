# Phase 2 Plan: Multi-Model + Prompt Management

**Phase**: 2 (Multi-Model + Prompt Management)
**Scope**: 3 working OCR model wrappers + Agenta.ai prompt sync + Prompt CRUD API + Pipeline Visualization
**Goal**: Replace all OCR stubs with working adapters, add bidirectional Agenta.ai prompt management, and provide an interactive pipeline diagram
**Prerequisite**: Phase 1 (MVP Backend API) — complete

---

## What We Are Building

1. **PaddleOCR wrapper** — local model, EN+JA, configurable languages/GPU, lazy-loaded
2. **EasyOCR wrapper** — local model, EN+JA, configurable languages/GPU, lazy-loaded
3. **Generic Vision API adapter** — replaces GLM OCR stub; sends base64 image to any OpenAI-compatible vision endpoint (OpenRouter, ZhipuAI, etc.)
4. **Agenta.ai client** — bidirectional prompt sync using the official Agenta Python SDK; Agenta is source of truth
5. **Prompt CRUD API** — full REST API for prompt versions: list, create, get, update, delete, activate, diff, sync
6. **Prompt Management UI** — 4 new frontend pages for managing prompts with markdown editor and diff viewer
7. **Pipeline Visualization** — React Flow interactive diagram showing pipeline stages with per-node config and live status
8. **Prompt version tracking** — pipeline results now record which prompt_version was used during extraction

## What We Are NOT Building (Yet)

- No social media URL fetching (Phase 2D — explicitly excluded)
- No evaluation / gold standard system (Phase 3)
- No results comparison viewer (Phase 3)
- No WebSocket real-time updates (Phase 4)
- No Docker for the app itself (Phase 4)
- No model fine-tuning
- No automated A/B testing of prompt versions
- No authentication

---

## Target Directory Structure

```
manga_ocr/                              # Project root
  ocr_manga_title/
    engine/
      paddle_model.py                   # REPLACED — working PaddleOCR wrapper
      easyocr_model.py                  # REPLACED — working EasyOCR wrapper
      glm_ocr_model.py                  # REPLACED — generic Vision API adapter
      registry.py                       # UPDATED — new params for each model
    agenta_client.py                    # NEW — Agenta.ai sync client
    api/
      app.py                            # UPDATED — register prompts router
      schemas/
        prompts.py                      # NEW — prompt request/response models
      routes/
        prompts.py                      # NEW — prompt CRUD endpoints
    postprocess/
      llm_extractor.py                  # UPDATED — accept prompt content from caller
    services/
      pipeline.py                       # UPDATED — track prompt_version_id
    workers/
      ocr_worker.py                     # UPDATED — load prompt from DB, pass version_id
    settings.py                         # UPDATED — add Agenta settings
  migrations/
    versions/
      006_add_prompt_sync_fields.py     # NEW — add source/sync columns to prompt_versions
  config/
    ocrs.yaml                           # UPDATED — add vision_api params
  prompts/
    llm/
      extract_title_v1.md               # Unchanged
  frontend/
    src/
      api/
        prompts.ts                      # NEW — prompt API functions
        types.ts                        # UPDATED — prompt TypeScript types
        client.ts                       # UPDATED — barrel export
      components/
        PipelineDiagram.tsx             # NEW — React Flow pipeline diagram
        NodeConfigPanel.tsx             # NEW — node detail sidebar
      pages/
        Prompts.tsx                     # NEW — prompt list page
        PromptDetail.tsx                # NEW — prompt version history
        PromptEditor.tsx                # NEW — create/edit prompt
        PromptDiff.tsx                  # NEW — diff two versions
      App.tsx                           # UPDATED — add prompt routes
    package.json                        # UPDATED — add @xyflow/react
  tests/
    test_engine/
      test_paddle_model.py              # NEW — mocked PaddleOCR tests
      test_easyocr_model.py             # NEW — mocked EasyOCR tests
      test_vision_api_model.py          # NEW — mocked Vision API tests
    test_api/
      test_prompts.py                   # NEW — prompt API route tests
    test_agenta/
      __init__.py                       # NEW
      test_client.py                    # NEW — Agenta sync tests
  pyproject.toml                        # UPDATED — new deps
```

---

## Implementation Steps

### Step 1: Update Dependencies

**Task**: Add new Python and frontend dependencies.

**Python deps** (add to `pyproject.toml`):
```
paddleocr>=2.8
easyocr>=1.7
agenta>=0.5
```

**Frontend deps** (add to `frontend/package.json`):
```
@xyflow/react  (React Flow v12)
```

**Files modified**:
- `pyproject.toml`
- `frontend/package.json`

---

### Step 2: PaddleOCR Model Wrapper

**Task**: Replace stub in `ocr_manga_title/engine/paddle_model.py` with a working PaddleOCR adapter.

**Behavior**:
- Lazy model loading: `PaddleModel()` constructor stores config; first call to `run()` creates `PaddleOCR` instance
- Model stored as `self._ocr` instance attribute (singleton per `PaddleModel` instance)
- `is_available` is dynamic: checks if `paddleocr` package is importable via `importlib.util.find_spec("paddleocr")`
- Config via `ModelConfig.parameters`: `languages` (list, default `["en", "ja"]`), `use_gpu` (bool, default `False`), `det_model_dir` (str, optional), `rec_model_dir` (str, optional)
- Returns `OCRResult` with:
  - `raw_text`: all detected text lines joined with newlines
  - `confidence`: mean of per-line confidences from PaddleOCR output (0.0 if no text)
  - `processing_time_ms`: measured with `time.monotonic()`
  - `model_name`: `"paddle"`
- Error handling:
  - `paddleocr` not importable → `is_available=False`, `run()` raises `ModelNotAvailableError`
  - Corrupt/unreadable image → return `OCRResult` with empty text, confidence=0.0, error message
  - CUDA error → log warning, fall back to CPU

**PaddleOCR Integration**:
```python
from paddleocr import PaddleOCR

class PaddleModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._ocr: PaddleOCR | None = None

    @property
    def name(self) -> str:
        return "paddle"

    @property
    def is_available(self) -> bool:
        return importlib.util.find_spec("paddleocr") is not None

    def _load_model(self) -> PaddleOCR:
        if self._ocr is None:
            params = self._config.parameters or {}
            lang = params.get("languages", ["en", "ja"])
            # PaddleOCR uses 'japan' not 'ja'
            lang_map = {"en": "en", "ja": "japan", "jpn": "japan"}
            paddle_lang = lang_map.get(lang[0], lang[0]) if isinstance(lang, list) else lang
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=paddle_lang,
                use_gpu=params.get("use_gpu", False),
                show_log=False,
            )
        return self._ocr

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("PaddleOCR is not installed")
        start = time.monotonic()
        try:
            ocr = self._load_model()
            result = ocr.ocr(image_path, cls=True)
            # result = [ [ [box, (text, confidence)], ... ] ]
            texts = []
            confidences = []
            for page in result or []:
                for line in page or []:
                    if line and len(line) >= 2:
                        texts.append(line[1][0])
                        confidences.append(line[1][1])
            raw_text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=round(avg_conf, 4),
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

**Files modified**:
- `ocr_manga_title/engine/paddle_model.py`

---

### Step 3: EasyOCR Model Wrapper

**Task**: Replace stub in `ocr_manga_title/engine/easyocr_model.py` with a working EasyOCR adapter.

**Behavior**:
- Lazy model loading: first `run()` call creates `easyocr.Reader` instance
- Model stored as `self._reader` instance attribute
- `is_available` is dynamic: checks if `easyocr` package is importable via `importlib.util.find_spec("easyocr")`
- Config via `ModelConfig.parameters`: `languages` (list, default `["en", "ja"]`), `gpu` (bool, default `False`), `model_storage_directory` (str, optional)
- Returns `OCRResult` with:
  - `raw_text`: all detected text lines joined with newlines
  - `confidence`: mean of per-word confidences from EasyOCR output
  - `processing_time_ms`: measured with `time.monotonic()`
  - `model_name`: `"easyocr"`
- Error handling:
  - `easyocr` not importable → `is_available=False`, `run()` raises `ModelNotAvailableError`
  - Corrupt/unreadable image → return `OCRResult` with empty text, confidence=0.0, error message
  - GPU error → log warning, fall back to CPU

**EasyOCR Integration**:
```python
import easyocr

class EasyOCRModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._reader = None

    @property
    def name(self) -> str:
        return "easyocr"

    @property
    def is_available(self) -> bool:
        return importlib.util.find_spec("easyocr") is not None

    def _load_reader(self):
        if self._reader is None:
            params = self._config.parameters or {}
            langs = params.get("languages", ["en", "ja"])
            self._reader = easyocr.Reader(
                langs,
                gpu=params.get("gpu", False),
                model_storage_directory=params.get("model_storage_directory"),
            )
        return self._reader

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("EasyOCR is not installed")
        start = time.monotonic()
        try:
            reader = self._load_reader()
            results = reader.readtext(image_path)
            # results = [ (bbox, text, confidence), ... ]
            texts = [r[1] for r in results]
            confidences = [r[2] for r in results]
            raw_text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=round(avg_conf, 4),
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

**Files modified**:
- `ocr_manga_title/engine/easyocr_model.py`

---

### Step 4: Generic Vision API Adapter

**Task**: Replace GLM OCR stub in `ocr_manga_title/engine/glm_ocr_model.py` with a generic vision API adapter that works with any OpenAI-compatible vision endpoint.

**Behavior**:
- Uses `openai.OpenAI` client (already a dependency) with configurable `base_url` and `api_key`
- Sends image as base64 data URL in a chat completions request
- Config via `ModelConfig.parameters`:
  - `api_endpoint` (str, required) — base URL for the API (e.g. `"https://openrouter.ai/api/v1"`)
  - `api_key` (str, optional) — API key; falls back to OpenRouter key from `configs.toml`
  - `model` (str, default `"google/gemini-2.5-flash"`) — model identifier at the endpoint
  - `prompt` (str, default `"Extract all text from this image."`) — text prompt sent with the image
  - `max_tokens` (int, default `4096`)
  - `temperature` (float, default `0.1`)
- `is_available` is dynamic: returns `True` if `api_endpoint` is non-empty in config parameters
- No lazy loading needed (no local model to load — just an HTTP client)
- Returns `OCRResult` with:
  - `raw_text`: the model's response text
  - `confidence`: estimated as 0.8 for clean responses, 0.5 if response seems truncated, 0.0 on error
  - `processing_time_ms`: measured with `time.monotonic()`
  - `model_name`: `"glm_ocr"`
- Error handling:
  - `api_endpoint` empty → `is_available=False`, `run()` raises `ModelNotAvailableError`
  - API timeout/error → return `OCRResult` with error message
  - Rate limit (429) → return `OCRResult` with error, log warning
  - Invalid response → return `OCRResult` with empty text

**Vision API Integration**:
```python
class GLMOCRModel(BaseOCRModel):
    def __init__(self, config: ModelConfig):
        self._config = config
        self._client = None

    @property
    def name(self) -> str:
        return "glm_ocr"

    @property
    def is_available(self) -> bool:
        params = self._config.parameters or {}
        return bool(params.get("api_endpoint"))

    def _get_client(self):
        if self._client is None:
            params = self._config.parameters or {}
            self._client = openai.OpenAI(
                base_url=params.get("api_endpoint", ""),
                api_key=params.get("api_key", ""),
            )
        return self._client

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def run(self, image_path: str) -> OCRResult:
        if not self.is_available:
            raise ModelNotAvailableError("Vision API endpoint not configured")
        start = time.monotonic()
        try:
            client = self._get_client()
            params = self._config.parameters or {}
            ext = Path(image_path).suffix.lower().lstrip(".")
            mime = {
                "png": "image/png",
                "jpg": "image/jpeg",
                "jpeg": "image/jpeg",
                "webp": "image/webp",
            }.get(ext, "image/png")
            b64 = self._encode_image(image_path)
            response = client.chat.completions.create(
                model=params.get("model", "google/gemini-2.5-flash"),
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": params.get(
                                    "prompt", "Extract all text from this image."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime};base64,{b64}"
                                },
                            },
                        ],
                    }
                ],
                max_tokens=params.get("max_tokens", 4096),
                temperature=params.get("temperature", 0.1),
            )
            raw_text = response.choices[0].message.content or ""
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text=raw_text,
                model_name=self.name,
                confidence=0.8 if raw_text else 0.0,
                processing_time_ms=elapsed_ms,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return OCRResult(
                raw_text="",
                model_name=self.name,
                confidence=0.0,
                processing_time_ms=elapsed_ms,
                error=str(e),
            )
```

**Files modified**:
- `ocr_manga_title/engine/glm_ocr_model.py`

---

### Step 5: Update Model Registry + Config

**Task**: Update `registry.py` with new parameter descriptors for PaddleOCR, EasyOCR, and Vision API models. Update `ocrs.yaml`.

**Registry Updates** (`ocr_manga_title/engine/registry.py`):

PaddleOCR params:
```python
ParamDescriptor(
    name="languages", type="multiselect", default=["en", "ja"],
    options=["en", "ja", "ch", "ko"], label="Languages",
    description="OCR languages",
),
ParamDescriptor(
    name="use_gpu", type="boolean", default=False,
    label="Use GPU", description="Enable CUDA acceleration",
),
```

EasyOCR params:
```python
ParamDescriptor(
    name="languages", type="multiselect", default=["en", "ja"],
    options=["en", "ja", "ch_sim", "ch_tra", "ko"], label="Languages",
    description="OCR languages",
),
ParamDescriptor(
    name="gpu", type="boolean", default=False,
    label="Use GPU", description="Enable CUDA acceleration",
),
```

Vision API params:
```python
ParamDescriptor(
    name="api_endpoint", type="select", default="",
    label="API Endpoint", description="Vision API base URL",
),
ParamDescriptor(
    name="model", type="select", default="google/gemini-2.5-flash",
    label="Model", description="Vision model identifier",
),
ParamDescriptor(
    name="api_key", type="select", default="",
    label="API Key",
    description="API key (leave empty to use OpenRouter key)",
),
ParamDescriptor(
    name="prompt", type="select",
    default="Extract all text from this image.",
    label="Extraction Prompt",
    description="Prompt sent with the image",
),
```

**Config Updates** (`config/ocrs.yaml`):
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
    use_gpu: false
  easyocr:
    enabled: false
    languages: ["en", "ja"]
    gpu: false
  glm_ocr:
    enabled: false
    api_endpoint: ""
    model: "google/gemini-2.5-flash"
    api_key: ""
    prompt: "Extract all text from this image."
```

**Seed Migration Update** (`migrations/versions/002_seed_models.py`): Update the glm_ocr parameters JSONB to include the new fields.

**Files modified**:
- `ocr_manga_title/engine/registry.py`
- `config/ocrs.yaml`
- `migrations/versions/002_seed_models.py`

---

### Step 6: Agenta Settings + Client

**Task**: Add Agenta.ai configuration to settings and create the sync client.

**Settings Updates** (`ocr_manga_title/settings.py`):
```python
AGENTA_API_KEY = os.environ.get("AGENTA_API_KEY", "")
AGENTA_BASE_URL = os.environ.get("AGENTA_BASE_URL", "https://api.agenta.ai")
AGENTA_APP_ID = os.environ.get("AGENTA_APP_ID", "")
AGENTA_SYNC_ON_STARTUP = os.environ.get("AGENTA_SYNC_ON_STARTUP", "false").lower() == "true"
```

**Agenta Client** (`ocr_manga_title/agenta_client.py`):

```python
class AgentaClient:
    def __init__(self, api_key: str, base_url: str, app_id: str):
        self._api_key = api_key
        self._base_url = base_url
        self._app_id = app_id

    async def pull_prompts(self, session: AsyncSession) -> list[PromptVersion]:
        """Fetch all prompts from Agenta, upsert into prompt_versions table.
        Returns list of created/updated PromptVersion rows."""

    async def push_prompt(
        self, session: AsyncSession, prompt_version_id: UUID
    ) -> PromptVersion | None:
        """Push a local prompt version to Agenta.
        Updates the prompt_version's agenta_id with the remote ID.
        Returns updated PromptVersion or None if Agenta is unreachable."""

    async def sync(self, session: AsyncSession) -> dict:
        """Bidirectional sync: pull from Agenta, then push any local-only versions.
        Returns {"pulled": N, "pushed": N, "conflicts": N, "errors": [...]}."""

    def is_configured(self) -> bool:
        """Check if Agenta credentials are set."""
        return bool(self._api_key and self._base_url and self._app_id)
```

**Pull Logic**:
1. Call Agenta API to list all prompt variants for the app
2. For each remote prompt:
   - If `agenta_id` matches an existing `PromptVersion` in DB → update content if remote is newer
   - If no match → create new `PromptVersion` row with `source="agenta"`
3. Set `last_synced_at` on synced rows

**Push Logic**:
1. Find the `PromptVersion` by ID
2. If it has `agenta_id` → update the remote prompt via Agenta API
3. If no `agenta_id` → create a new prompt variant in Agenta, store the returned ID

**Conflict Resolution**: Agenta version wins if `updated_at` timestamps differ (Agenta is source of truth per PHASES.md).

**Offline Fallback**: If Agenta is unreachable, all methods return gracefully with error info. Pipeline uses DB-stored prompts as fallback.

**Files created**:
- `ocr_manga_title/agenta_client.py`

**Files modified**:
- `ocr_manga_title/settings.py`
- `.env.example`

---

### Step 7: DB Migration — Prompt Sync Fields

**Task**: Add sync tracking columns to `prompt_versions` table.

**Migration** (`migrations/versions/006_add_prompt_sync_fields.py`):
```python
def upgrade():
    op.add_column(
        "prompt_versions",
        sa.Column("source", sa.String(), nullable=True, server_default="local"),
    )
    op.add_column(
        "prompt_versions",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("prompt_versions", "last_synced_at")
    op.drop_column("prompt_versions", "source")
```

**New columns**:
- `source: str | None` — `"local"` (created in UI), `"agenta"` (pulled from Agenta), `"seed"` (initial migration)
- `last_synced_at: datetime | None` — last successful sync timestamp

**ORM Model Update** (`ocr_manga_title/db/models.py`):
```python
class PromptVersion(Base):
    # ... existing columns ...
    source: Mapped[str | None] = mapped_column(default="local")
    last_synced_at: Mapped[datetime | None]
```

**Files created**:
- `migrations/versions/006_add_prompt_sync_fields.py`

**Files modified**:
- `ocr_manga_title/db/models.py`

---

### Step 8: Prompt CRUD Operations

**Task**: Add prompt CRUD functions to `ocr_manga_title/db/crud.py`.

**New Functions**:
```python
async def create_prompt_version(
    session, prompt_type: str, content: str,
    version_number: int, tags: str | None = None,
    source: str = "local",
) -> PromptVersion

async def get_prompt_version(session, version_id: UUID) -> PromptVersion | None

async def update_prompt_version(
    session, version_id: UUID, **kwargs
) -> PromptVersion | None
    # Updatable: content, tags, agenta_id, source, last_synced_at

async def delete_prompt_version(session, version_id: UUID) -> bool
    # Soft delete: deactivate. Hard delete only if no post_processing_results reference it.
    # Returns True if deleted, False if not found or referenced.

async def activate_prompt_version(
    session, version_id: UUID
) -> PromptVersion | None
    # Deactivate all other versions of the same prompt_type, activate this one.
    # Returns activated PromptVersion or None.

async def count_prompt_versions(
    session, prompt_type: str | None = None
) -> int

async def get_next_version_number(session, prompt_type: str) -> int
    # Returns max(version_number) + 1 for the given prompt_type.
```

**Existing functions** (already in crud.py, no changes needed):
- `get_active_prompt(session, prompt_type)` — returns active prompt for a type
- `list_prompts(session, prompt_type=None)` — all versions, newest first

**Files modified**:
- `ocr_manga_title/db/crud.py`

---

### Step 9: Prompt API Schemas

**Task**: `ocr_manga_title/api/schemas/prompts.py` — request/response Pydantic models.

**Request Models**:
```python
class PromptVersionCreateRequest(BaseModel):
    prompt_type: str = Field(
        pattern="^(llm)$", description="Prompt type (currently only 'llm')"
    )
    content: str = Field(min_length=1, max_length=50000)
    tags: str | None = None


class PromptVersionUpdateRequest(BaseModel):
    content: str | None = Field(
        min_length=1, max_length=50000, default=None
    )
    tags: str | None = None


class PromptActivateRequest(BaseModel):
    pass  # No body needed, but explicit for OpenAPI docs


class PromptDiffRequest(BaseModel):
    other_version_id: UUID
```

**Response Models**:
```python
class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_type: str
    content: str
    version_number: int
    agenta_id: str | None
    is_active: bool
    tags: str | None
    source: str | None
    last_synced_at: datetime | None
    created_at: datetime


class PromptVersionListResponse(BaseModel):
    items: list[PromptVersionResponse]
    total: int


class PromptDiffResponse(BaseModel):
    version_a: PromptVersionResponse
    version_b: PromptVersionResponse
    diff: list[DiffLine]


class DiffLine(BaseModel):
    type: str  # "added" | "removed" | "unchanged"
    content: str
    line_number_a: int | None
    line_number_b: int | None


class PromptSyncResponse(BaseModel):
    pulled: int
    pushed: int
    conflicts: int
    errors: list[str]
```

**Files created**:
- `ocr_manga_title/api/schemas/prompts.py`

**Files modified**:
- `ocr_manga_title/api/schemas/__init__.py` (add re-export)

---

### Step 10: Prompt API Routes

**Task**: `ocr_manga_title/api/routes/prompts.py` — full CRUD + sync + diff endpoints.

**Endpoints**:

`GET /api/v1/prompts`:
- Query params: `prompt_type` (optional filter), `limit` (default 50), `offset` (default 0)
- Return `PromptVersionListResponse`
- Sorted by `version_number` descending

`POST /api/v1/prompts`:
- Body: `PromptVersionCreateRequest`
- Auto-assign `version_number` via `get_next_version_number()`
- Set `source="local"`, `is_active=False`
- If Agenta is configured, push to Agenta asynchronously (fire-and-forget, don't block response)
- Return `PromptVersionResponse` with 201 status

`GET /api/v1/prompts/{version_id}`:
- Return `PromptVersionResponse`
- 404 if not found

`PUT /api/v1/prompts/{version_id}`:
- Body: `PromptVersionUpdateRequest`
- Update content and/or tags
- If content changed and Agenta is configured, push update to Agenta
- Return updated `PromptVersionResponse`
- 404 if not found

`DELETE /api/v1/prompts/{version_id}`:
- If `is_active=True` → return 409 "Cannot delete active prompt version"
- If referenced by `post_processing_results` → deactivate only (soft delete)
- Otherwise → hard delete
- Return 204

`POST /api/v1/prompts/{version_id}/activate`:
- Deactivate all other versions of same `prompt_type`
- Activate this version
- Return activated `PromptVersionResponse`
- 404 if not found

`POST /api/v1/prompts/sync`:
- Trigger bidirectional sync with Agenta
- If Agenta not configured → return 503 "Agenta not configured"
- Return `PromptSyncResponse`

`GET /api/v1/prompts/{version_id}/diff/{other_version_id}`:
- Return `PromptDiffResponse` with unified diff between the two versions
- 404 if either version not found
- Both versions must have same `prompt_type` (400 if mismatch)

**Files created**:
- `ocr_manga_title/api/routes/prompts.py`

---

### Step 11: Register Prompts Router + Agenta Startup

**Task**: Register the prompts router in `app.py` and optionally trigger Agenta sync on startup.

**App Factory Update** (`ocr_manga_title/api/app.py`):
```python
from ocr_mocr_title.api.routes import prompts

app.include_router(
    prompts.router, prefix="/api/v1/prompts", tags=["prompts"]
)
```

**Lifespan Update**:
- If `AGENTA_SYNC_ON_STARTUP=true` → trigger background sync on app startup
- Use `asyncio.create_task()` to avoid blocking startup

**Files modified**:
- `ocr_manga_title/api/app.py`

---

### Step 12: LLM Extractor Refactor

**Task**: Refactor `ocr_manga_title/postprocess/llm_extractor.py` to accept prompt content from caller instead of always loading from file.

**Current**: Constructor loads prompt from `prompts/llm/extract_title_v1.md` (or custom path).

**New**:
```python
class LLMExtractor:
    def __init__(
        self,
        config: OpenRouterConfig,
        prompt_content: str | None = None,
        prompt_path: Path | None = None,
    ):
        self._client = openai.OpenAI(
            api_key=config.api_key, base_url=config.base_url
        )
        if prompt_content:
            self._system_prompt = prompt_content
        elif prompt_path:
            self._system_prompt = prompt_path.read_text()
        else:
            self._system_prompt = self._FALLBACK_PROMPT
```

**Key Changes**:
- New `prompt_content` parameter: if provided, use it directly (from DB `prompt_versions.content`)
- `prompt_path` parameter: kept as fallback (from file)
- If neither provided: use hardcoded `_FALLBACK_PROMPT`
- `extract()` method unchanged — it already uses `self._system_prompt`
- New property: `used_prompt_content: str` — returns the active prompt text (for verification/logging)

**Files modified**:
- `ocr_manga_title/postprocess/llm_extractor.py`

---

### Step 13: Worker Prompt Integration

**Task**: Update `ocr_manga_title/workers/ocr_worker.py` to load the active prompt from DB and pass it (and `prompt_version_id`) through the pipeline.

**Current Flow**:
1. Worker creates `OCREngine(config, model_configs, preprocess_config)`
2. Engine creates `LLMExtractor(config)` → loads prompt from file
3. `save_pipeline_results()` never sets `prompt_version_id`

**New Flow**:
1. Worker fetches active prompt: `await get_active_prompt(session, prompt_type="llm")`
2. Worker creates `OCREngine(config, model_configs, preprocess_config, prompt_content=prompt.content, prompt_version_id=prompt.id)`
3. Engine passes `prompt_content` to `LLMExtractor(config, prompt_content=prompt_content)`
4. Engine returns `prompt_version_id` in `PipelineResult` (new field)
5. `save_pipeline_results()` sets `prompt_version_id` on each `PostProcessingResult`

**PipelineResult Schema Update** (`ocr_manga_title/schemas.py`):
```python
class PipelineResult:
    # ... existing fields ...
    prompt_version_id: UUID | None = None  # NEW
```

**OCREngine Update** (`ocr_manga_title/engine/ocr_engine.py`):
```python
class OCREngine:
    def __init__(
        self, config, ocr_config, preprocess_config=None,
        prompt_content: str | None = None,
        prompt_version_id: UUID | None = None,
    ):
        self._prompt_version_id = prompt_version_id
        self._llm_extractor = LLMExtractor(
            config.openrouter, prompt_content=prompt_content
        )
```

**save_pipeline_results Update** (`ocr_manga_title/services/pipeline.py`):
- Accept `prompt_version_id: UUID | None` parameter
- Set it on each `PostProcessingResult` row

**Files modified**:
- `ocr_manga_title/workers/ocr_worker.py`
- `ocr_manga_title/engine/ocr_engine.py`
- `ocr_manga_title/schemas.py`
- `ocr_manga_title/services/pipeline.py`

---

### Step 14: Frontend Prompt API + Types

**Task**: Create TypeScript types and API functions for prompts.

**Types** (`frontend/src/api/types.ts` — additions):
```typescript
export interface PromptVersionResponse {
  id: string
  prompt_type: string
  content: string
  version_number: number
  agenta_id: string | null
  is_active: boolean
  tags: string | null
  source: string | null
  last_synced_at: string | null
  created_at: string
}

export interface PromptVersionListResponse {
  items: PromptVersionResponse[]
  total: number
}

export interface PromptDiffResponse {
  version_a: PromptVersionResponse
  version_b: PromptVersionResponse
  diff: DiffLine[]
}

export interface DiffLine {
  type: "added" | "removed" | "unchanged"
  content: string
  line_number_a: number | null
  line_number_b: number | null
}

export interface PromptSyncResponse {
  pulled: number
  pushed: number
  conflicts: number
  errors: string[]
}
```

**API Functions** (`frontend/src/api/prompts.ts`):
```typescript
export async function listPrompts(params?: {
  prompt_type?: string
  limit?: number
  offset?: number
}): Promise<PromptVersionListResponse>

export async function createPrompt(data: {
  prompt_type: string
  content: string
  tags?: string
}): Promise<PromptVersionResponse>

export async function getPrompt(
  versionId: string
): Promise<PromptVersionResponse>

export async function updatePrompt(
  versionId: string,
  data: { content?: string; tags?: string }
): Promise<PromptVersionResponse>

export async function deletePrompt(versionId: string): Promise<void>

export async function activatePrompt(
  versionId: string
): Promise<PromptVersionResponse>

export async function syncPrompts(): Promise<PromptSyncResponse>

export async function diffPrompts(
  versionIdA: string
  versionIdB: string
): Promise<PromptDiffResponse>
```

**Files created**:
- `frontend/src/api/prompts.ts`

**Files modified**:
- `frontend/src/api/types.ts`
- `frontend/src/api/client.ts` (barrel export)

---

### Step 15: Frontend Prompt Pages

**Task**: Create 4 new pages for prompt management.

**Prompts List** (`frontend/src/pages/Prompts.tsx`):
- Page title: "Prompt Versions"
- Filter tabs by `prompt_type` (currently only "llm")
- Table: Version #, Content (truncated 60 chars), Status (active/inactive with LED dot), Source badge (local/agenta), Tags, Created, Actions
- Actions: View, Edit, Activate, Delete
- "New Prompt" button (top-right, teal primary)
- "Sync with Agenta" button (top-right, amber secondary, disabled if not configured)
- Pagination controls
- DSO dark theme: neo-panel cards, DsoTable, DsoPagination

**Prompt Detail** (`frontend/src/pages/PromptDetail.tsx`):
- Route: `/prompts/:id`
- Shows full prompt content in a `<pre>` block (LCD screen style)
- Metadata sidebar: version number, type, source, tags, created_at, agenta_id, last_synced_at
- Action buttons: Edit, Activate, Delete, Diff with another version
- Version history timeline at bottom (list of all versions with links)
- Back link to Prompts list

**Prompt Editor** (`frontend/src/pages/PromptEditor.tsx`):
- Route: `/prompts/new` and `/prompts/:id/edit`
- Two-column layout:
  - Left: textarea with monospace font for prompt content (resizable, min 300px height)
  - Right: live preview rendered as markdown
- Fields: prompt_type (dropdown), content (textarea), tags (text input)
- Buttons: "Create/Save" (teal primary), "Cancel" (ghost)
- Validation: content required, min 10 chars

**Prompt Diff** (`frontend/src/pages/PromptDiff.tsx`):
- Route: `/prompts/:id/diff/:otherId`
- Two-column side-by-side view
- Left: version A content with colored lines (red for removed)
- Right: version B content with colored lines (green for added)
- Header shows version numbers and metadata for each
- Dropdown to change comparison version
- DSO LCD screen styling for the diff panels

**Files created**:
- `frontend/src/pages/Prompts.tsx`
- `frontend/src/pages/PromptDetail.tsx`
- `frontend/src/pages/PromptEditor.tsx`
- `frontend/src/pages/PromptDiff.tsx`

---

### Step 16: App Shell — Prompt Routes

**Task**: Add prompt page routes to `App.tsx` and navigation dropdown.

**Routes Added**:
```typescript
<Route path="/prompts" element={<Prompts />} />
<Route path="/prompts/new" element={<PromptEditor />} />
<Route path="/prompts/:id" element={<PromptDetail />} />
<Route path="/prompts/:id/edit" element={<PromptEditor />} />
<Route
  path="/prompts/:id/diff/:otherId"
  element={<PromptDiff />}
/>
```

**Navigation Update**:
- Add "Prompts" to the Config dropdown (alongside Profiles)
- Or create new "Config" group entry: "Prompt Versions"

**Files modified**:
- `frontend/src/App.tsx`

---

### Step 17: React Flow Pipeline Diagram Component

**Task**: Create the interactive pipeline visualization component.

**`PipelineDiagram` Component** (`frontend/src/components/PipelineDiagram.tsx`):

**Node Types** (6 nodes in a left-to-right flow):
1. **Input** — icon: image upload, shows filename
2. **OCR Models** — icon: scanner, lists enabled models (one sub-badge per model)
3. **Text Aggregation** — icon: merge, shows text count
4. **LLM Post-Processing** — icon: brain, shows active prompt version number
5. **Rule Matching** — icon: filter, shows rules applied
6. **Output** — icon: check, shows extracted title

**Layout**:
```
[Input] → [OCR Models] → [Text Aggregation] → [LLM] → [Rules] → [Output]
```

**Node Styling** (DSO theme):
- Default: `bg-panel border border-highlight/20` with node icon and label
- Processing: `border-teal breathing` animation
- Completed: `border-teal` solid
- Error: `border-amber` with error icon
- Idle: default muted appearance

**Custom Nodes**: Each node is a custom React Flow node component:
- `InputNode` — shows image thumbnail (64x64), filename
- `ModelGroupNode` — shows list of enabled models with status LEDs
- `MergeNode` — shows count of text outputs
- `LLMNode` — shows model name + prompt version
- `RuleNode` — shows rule types (ISBN, normalization)
- `OutputNode` — shows extracted title_en + confidence

**Edges**: Simple bezier curves, `stroke: teal`, animated when processing.

**Interactivity**:
- Click node → calls `onNodeClick(nodeId)` callback
- Zoom/pan enabled
- Minimap in bottom-right corner
- Fit view on load

**Props**:
```typescript
interface PipelineDiagramProps {
  run?: PipelineRunDetailResponse    // If provided, shows real data + status
  enabledModels?: string[]           // For static/empty diagram
  activePromptVersion?: number       // For static diagram
  className?: string
}
```

**`NodeConfigPanel` Component** (`frontend/src/components/NodeConfigPanel.tsx`):
- Sidebar that appears when a node is clicked
- Shows node-specific config details:
  - Input: image path, source, upload date
  - OCR Models: list of models with params (language, PSM, GPU, etc.)
  - LLM: prompt version content preview, model name
  - Rules: regex patterns, normalization rules
  - Output: title_en, title_ja, code, confidence
- Close button (X) to dismiss
- DSO neo-panel styling

**Files created**:
- `frontend/src/components/PipelineDiagram.tsx`
- `frontend/src/components/NodeConfigPanel.tsx`

---

### Step 18: Integrate Diagram into Pages

**Task**: Add the pipeline diagram to appropriate pages.

**Run Detail Page** (`frontend/src/pages/RunDetail.tsx`):
- Add `PipelineDiagram` between the run header and OCR results sections
- Pass the full run detail data to the diagram
- Status colors reflect actual run status per node
- Click node → show `NodeConfigPanel` with real data

**Dashboard Page** (`frontend/src/pages/Dashboard.tsx`):
- Replace or augment the bottom-left "Tactical Controls" panel with a static mini pipeline diagram
- Shows currently enabled models and active prompt version
- No interactivity (no click handlers) — purely informational
- Compact layout (smaller nodes, no minimap)

**Files modified**:
- `frontend/src/pages/RunDetail.tsx`
- `frontend/src/pages/Dashboard.tsx`

---

### Step 19: Tests

**Task**: Tests for new OCR models, Agenta client, prompt API routes, and prompt CRUD.

**Model Tests** (`tests/test_engine/`):

`test_paddle_model.py`:
- `test_is_available_returns_true_when_paddleocr_installed` (mock `find_spec`)
- `test_is_available_returns_false_when_paddleocr_missing` (mock `find_spec` to None)
- `test_run_returns_ocr_result_with_text` (mock `PaddleOCR.ocr()`)
- `test_run_returns_empty_on_corrupt_image` (mock raises exception)
- `test_run_raises_when_not_available` (mock `is_available=False`)
- `test_lazy_load_creates_model_on_first_run` (verify singleton)
- `test_configurable_language_and_gpu` (verify params passed through)

`test_easyocr_model.py`:
- Same pattern as paddle tests
- `test_run_returns_ocr_result_with_text` (mock `reader.readtext()`)
- `test_reader_uses_configured_languages`

`test_vision_api_model.py`:
- `test_is_available_true_when_endpoint_set`
- `test_is_available_false_when_endpoint_empty`
- `test_run_sends_base64_image` (mock `openai.OpenAI`)
- `test_run_handles_api_error` (mock raises)
- `test_run_handles_rate_limit` (mock 429)
- `test_configurable_model_and_prompt`
- `test_uses_openrouter_key_fallback`

**Agenta Client Tests** (`tests/test_agenta/test_client.py`):
- `test_pull_creates_new_versions_from_agenta` (mock Agenta API)
- `test_pull_updates_existing_version` (mock with matching agenta_id)
- `test_push_creates_remote_prompt` (mock Agenta create)
- `test_push_updates_remote_prompt` (mock Agenta update)
- `test_sync_pulls_then_pushes` (integration mock)
- `test_offline_fallback_returns_gracefully` (mock connection error)
- `test_conflict_resolution_agenta_wins` (mock newer remote timestamp)
- `test_not_configured_returns_early` (empty credentials)

**Prompt API Route Tests** (`tests/test_api/test_prompts.py`):
- `test_list_prompts_returns_all` (seeded data)
- `test_list_prompts_filtered_by_type`
- `test_create_prompt_auto_increments_version`
- `test_create_prompt_pushes_to_agenta` (mock Agenta)
- `test_get_prompt_returns_version`
- `test_get_prompt_404_for_missing`
- `test_update_prompt_content`
- `test_delete_inactive_prompt`
- `test_delete_active_prompt_returns_409`
- `test_activate_prompt_deactivates_others`
- `test_sync_returns_pull_push_counts` (mock Agenta)
- `test_sync_503_when_agenta_not_configured`
- `test_diff_returns_unified_diff`
- `test_diff_400_for_mismatched_types`

**All tests**: use mocked external dependencies (no real PaddleOCR, EasyOCR, Agenta, or OpenAI calls), in-memory SQLite.

**Files created**:
- `tests/test_engine/test_paddle_model.py`
- `tests/test_engine/test_easyocr_model.py`
- `tests/test_engine/test_vision_api_model.py`
- `tests/test_api/test_prompts.py`
- `tests/test_agenta/__init__.py`
- `tests/test_agenta/test_client.py`

---

### Step 20: Configuration + Makefile Updates

**Task**: Update config files and Makefile for Phase 2.

**`.env.example` updates**:
```
# Agenta.ai (optional — leave empty to disable sync)
AGENTA_API_KEY=
AGENTA_BASE_URL=https://api.agenta.ai
AGENTA_APP_ID=
AGENTA_SYNC_ON_STARTUP=false
```

**`configs.toml` updates** — add vision API section (optional):
```toml
[vision_api]
default_endpoint = ""
default_model = "google/gemini-2.5-flash"
```

**Makefile updates**:
```makefile
test-all:     # Include test_engine/test_paddle_model.py, test_easyocr_model.py, test_vision_api_model.py, test_api/test_prompts.py, test_agenta/
setup-full:   # pip install paddleocr easyocr agenta (in addition to base setup)
```

**Files modified**:
- `.env.example`
- `config/configs.toml`
- `Makefile`

---

## API Endpoint Summary

| Method | Path | Description |
|--------|------|-------------|
| **Prompts** | | |
| GET | `/api/v1/prompts` | List prompt versions (filterable by type) |
| POST | `/api/v1/prompts` | Create prompt version (pushes to Agenta) |
| GET | `/api/v1/prompts/{id}` | Get prompt version content |
| PUT | `/api/v1/prompts/{id}` | Update prompt version (pushes to Agenta) |
| DELETE | `/api/v1/prompts/{id}` | Delete prompt version (soft if referenced) |
| POST | `/api/v1/prompts/{id}/activate` | Set as active prompt |
| POST | `/api/v1/prompts/sync` | Trigger bidirectional Agenta sync |
| GET | `/api/v1/prompts/{id}/diff/{other_id}` | Diff between two versions |

*(All existing endpoints from Phase 1 remain unchanged)*

---

## Acceptance Criteria for Phase 2

- [ ] `paddleocr` package installs and PaddleOCR model runs OCR on a test image
- [ ] `easyocr` package installs and EasyOCR model runs OCR on a test image
- [ ] Vision API adapter sends base64 image to configurable endpoint and returns text
- [ ] All 3 models report `is_available` dynamically based on installed packages / configured endpoints
- [ ] `GET /api/v1/prompts` lists prompt versions with filtering
- [ ] `POST /api/v1/prompts` creates a new version and auto-increments version_number
- [ ] `POST /api/v1/prompts/{id}/activate` deactivates others, activates this one
- [ ] `GET /api/v1/prompts/{id}/diff/{other_id}` returns unified diff
- [ ] `POST /api/v1/prompts/sync` pulls from Agenta and pushes local changes
- [ ] Worker loads active prompt from DB (not file), stores `prompt_version_id` on results
- [ ] `PostProcessingResult.prompt_version_id` is populated for new pipeline runs
- [ ] Frontend `/prompts` page lists versions with type filter and status indicators
- [ ] Frontend `/prompts/new` creates a prompt with markdown editor
- [ ] Frontend `/prompts/:id/diff/:otherId` shows side-by-side diff
- [ ] Pipeline diagram renders on RunDetail page with 6 nodes
- [ ] Diagram shows real data when viewing a completed run
- [ ] Diagram shows enabled models and active prompt on Dashboard
- [ ] All new tests pass (`make test-all`)
- [ ] No lint errors (`make lint`)

---

## Phase 1 Status (Pre-existing)

The following Phase 1 items are complete and unchanged:
- `ocr_manga_title/` package: config, schemas, engine, models, preprocess, postprocess, api, workers, db
- Frontend: 12 pages with DSO dark theme
- PostgreSQL + Redis + Dramatiq worker
- Batch runs, profiles, playgrounds
- All existing tests passing

The following Phase 1 gaps are explicitly excluded from Phase 2:
- Social media URL fetching (Phase 2D — excluded)
- Evaluation / gold standard (Phase 3)
- WebSocket real-time updates (Phase 4)
