# Config Profiles Implementation Plan

## 1. Executive Summary

**Problem**: Pipeline configuration is scattered across 4 sources (TOML, YAML, DB, env vars) with no way to save, name, or reuse a configuration. The worker loads global files on every run. The `PipelineRun.preprocess_config` column exists but is dormant. Quick Run already accepts inline config — the exact shape a profile would store.

**Solution**: Introduce a `PipelineProfile` DB table that captures the full pipeline config (preprocessing steps + OCR model selection/params + LLM toggle) as a named, reusable entity. Snapshot the profile into `PipelineRun.preprocess_config` at creation/enqueue time. Modify the worker to read the snapshot instead of global files. This eliminates the "worker reads global config" smell and unblocks per-run config customization for both individual and batch runs.

**Success Criteria**:
1. User can create, list, update, delete named profiles via API
2. Worker reads config from `PipelineRun.preprocess_config` snapshot (no more `load_preprocess_config()` or `_get_model_configs()` per run)
3. Batch creation accepts a `profile_id` — all child runs get the snapshot
4. Quick Run can optionally load a profile as defaults, with inline overrides
5. Frontend has a Profiles management page and profile picker on Upload/QuickRun
6. All 300+ existing tests continue to pass

---

## 2. Architecture

### Data Flow (After Implementation)

```
[Create Profile]                [Upload/Batch/QuickRun]
     │                                   │
     ▼                                   │
PipelineProfile DB row                   │
  - name                                 │
  - preprocess_steps (JSON)              │
  - ocr_models (JSON)                    │
  - enable_llm (bool)                    │
  - is_default (bool)                    │
     │                                   │
     └──────── profile_id ◄──────────────┘
                    │
                    ▼
        Snapshot into PipelineRun.preprocess_config (JSON)
                    │
                    ▼
        Worker reads snapshot → builds OCREngine
```

### Key Design Decisions

1. **Profile = combined config** (not separate preprocess/model profiles). Rationale: the QuickRunRequest shape (`preprocess_steps` + `ocr_models` + `enable_llm`) is already proven. Users think in terms of "my manga scan profile" not "my step 3 preset".

2. **Snapshot, not FK reference**. The profile is copied into `PipelineRun.preprocess_config` at creation time. Rationale: (a) the column already exists and is dormant, (b) profile edits don't retroactively affect old runs, (c) worker doesn't need a DB lookup to resolve the profile.

3. **Worker falls back to legacy path** if `preprocess_config` is null. This maintains backward compatibility for runs created before profiles exist.

4. **`is_default` flag** on exactly one profile. New runs/batches use the default profile when no `profile_id` is specified. If no default exists, falls back to current global-file behavior.

5. **Profile JSON shape** matches `QuickRunRequest` exactly:
   ```json
   {
     "preprocess_steps": {"roi": {"enabled": true, "min_area": 500}, ...},
     "ocr_models": {"tesseract": {"enabled": true, "languages": ["eng","jpn"], "psm": 6}, ...},
     "enable_llm": true
   }
   ```

---

## 3. Phase A: PipelineProfile (Backend)

### 3.1 Database Model

**File**: `ocr_manga_title/db/models.py` — add `PipelineProfile` class

```python
class PipelineProfile(Base):
    __tablename__ = "pipeline_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preprocess_steps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ocr_models: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    enable_llm: Mapped[bool] = mapped_column(Boolean, default=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
```

**Indexes**: `ix_pipeline_profiles_is_default` on `is_default`

### 3.2 Migration

**File**: `migrations/versions/005_add_pipeline_profile.py`

- Create `pipeline_profiles` table
- Seed a "Default" profile from current `config/preprocess.yaml` + DB `model_configs` + `enable_llm=true`

### 3.3 CRUD Functions

**File**: `ocr_manga_title/db/crud.py` — add 6 functions:

| Function | Signature | Description |
|---|---|---|
| `create_profile` | `(session, *, name, description?, preprocess_steps?, ocr_models?, enable_llm?, is_default?) -> PipelineProfile` | Insert profile. If `is_default=True`, unset any existing default first. |
| `get_profile` | `(session, profile_id) -> PipelineProfile \| None` | Fetch by UUID |
| `get_default_profile` | `(session) -> PipelineProfile \| None` | Fetch where `is_default=True` |
| `list_profiles` | `(session, limit?, offset?) -> list[PipelineProfile]` | Paginated list ordered by name |
| `count_profiles` | `(session) -> int` | Total count |
| `update_profile` | `(session, profile_id, **kwargs) -> PipelineProfile \| None` | Update fields. If setting `is_default=True`, unset any existing default first. |
| `delete_profile` | `(session, profile_id) -> bool` | Delete by UUID, return whether it existed |

### 3.4 API Schemas

**File**: `ocr_manga_title/api/schemas/profiles.py` — new file

```python
class ProfileResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    preprocess_steps: dict | None
    ocr_models: dict | None
    enable_llm: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime | None

class ProfileCreateRequest(BaseModel):
    name: str
    description: str | None = None
    preprocess_steps: dict[str, dict[str, Any]] | None = None
    ocr_models: dict[str, dict[str, Any]] | None = None
    enable_llm: bool = False
    is_default: bool = False

class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    preprocess_steps: dict[str, dict[str, Any]] | None = None
    ocr_models: dict[str, dict[str, Any]] | None = None
    enable_llm: bool | None = None
    is_default: bool | None = None
```

### 3.5 API Routes

**File**: `ocr_manga_title/api/routes/profiles.py` — new file, 6 endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/profiles` | Create profile |
| `GET` | `/profiles` | List profiles (paginated) |
| `GET` | `/profiles/{id}` | Get profile detail |
| `PUT` | `/profiles/{id}` | Update profile |
| `DELETE` | `/profiles/{id}` | Delete profile |
| `POST` | `/profiles/{id}/set-default` | Set as default (unsets previous) |

**Register in**: `ocr_manga_title/api/app.py` — add `profiles` router at `/api/v1/profiles`

### 3.6 Config Snapshot Helper

**File**: `ocr_manga_title/services/config.py` — new file

```python
def build_run_config_snapshot(
    profile: PipelineProfile | None,
) -> dict | None:
    """Build the JSON snapshot to store in PipelineRun.preprocess_config.
    
    If profile is None, returns None (worker will use legacy global-file path).
    """
    if profile is None:
        return None
    return {
        "preprocess_steps": profile.preprocess_steps or {},
        "ocr_models": profile.ocr_models or {},
        "enable_llm": profile.enable_llm,
    }
```

### 3.7 Wire Profile into PipelineRun Creation

**Modify**: `ocr_manga_title/api/routes/inputs.py` (`POST /upload`)
- Accept optional `profile_id: uuid.UUID | None = None` query param
- If provided, load profile, call `build_run_config_snapshot()`, pass as `preprocess_config` to `create_pipeline_run()`

**Modify**: `ocr_manga_title/api/routes/batches.py` (`POST /batches`)
- Accept optional `profile_id: uuid.UUID | None = None` form field
- Snapshot the profile config into each child `PipelineRun.preprocess_config`

**Modify**: `ocr_manga_title/api/routes/run.py` (`POST /quick`)
- Accept optional `profile_id: uuid.UUID | None = None` in `QuickRunRequest`
- If provided, load profile as base, merge with any inline overrides (inline takes precedence)

### 3.8 Worker: Read Snapshot Instead of Global Files

**Modify**: `ocr_manga_title/workers/ocr_worker.py` `_process()`

Current flow (lines 95-104):
```python
app_config = load_config(CONFIG_PATH)
model_configs = await _get_model_configs(session)
preprocess_config = load_preprocess_config(PREPROCESS_CONFIG_PATH)
engine = OCREngine(config=app_config, ocr_config=model_configs, preprocess_config=preprocess_config)
```

New flow:
```python
app_config = load_config(CONFIG_PATH)

if run.preprocess_config:
    # Profile snapshot path
    ocr_models = run.preprocess_config.get("ocr_models", {})
    model_configs = _build_model_configs_from_snapshot(ocr_models)
    preprocess_raw = _build_preprocess_raw(run.preprocess_config.get("preprocess_steps", {}))
    enable_llm = run.preprocess_config.get("enable_llm", False)
else:
    # Legacy fallback: global files + DB
    model_configs = await _get_model_configs(session)
    preprocess_raw = load_preprocess_config(PREPROCESS_CONFIG_PATH)
    enable_llm = True  # current default behavior

engine = OCREngine(config=app_config, ocr_config=model_configs, preprocess_config=preprocess_raw)
```

Add helper functions:
- `_build_model_configs_from_snapshot(ocr_models: dict) -> dict[str, ModelConfigSchema]` — converts the `ocr_models` JSON shape (same as `QuickRunRequest.ocr_models`) into `ModelConfig` Pydantic instances using `build_model_config()` from `services/ocr.py`
- `_build_preprocess_raw(preprocess_steps: dict) -> dict` — wraps into `{"preprocessing": {"enabled": True, "steps": ...}}` format that `PreProcessingPipeline` expects

**Note on LLM**: The `OCREngine` always runs LLM extraction. To honor `enable_llm=false`, we need a small change: pass the flag through and skip `_extract_titles()` when disabled. Alternatively, the simplest approach is to handle this in `_process()` — after `engine.process()`, check if LLM was disabled in the snapshot and strip post-processing results. This avoids modifying OCREngine.

**Chosen approach**: Skip LLM in `_process()` by not running `_extract_titles()`. But OCREngine always runs LLM internally... 

**Better approach**: Pass `enable_llm` to a new `OCREngine.process()` parameter:
```python
def process(self, image_path: str, *, enable_llm: bool = True) -> PipelineResult:
```
When `enable_llm=False`, skip `_extract_titles()` and only run rule matching. This is a 3-line change in `ocr_engine.py`.

---

## 4. Phase B: Frontend

### 4.1 API Client

**File**: `frontend/src/api/profiles.ts` — new file

```typescript
export async function listProfiles(limit?: number, offset?: number): Promise<PaginatedResponse<ProfileResponse>>
export async function getProfile(id: string): Promise<ProfileResponse>
export async function createProfile(data: ProfileCreateRequest): Promise<ProfileResponse>
export async function updateProfile(id: string, data: ProfileUpdateRequest): Promise<ProfileResponse>
export async function deleteProfile(id: string): Promise<void>
export async function setDefaultProfile(id: string): Promise<ProfileResponse>
```

**File**: `frontend/src/api/types.ts` — add types:

```typescript
export interface ProfileResponse {
  id: string;
  name: string;
  description: string | null;
  preprocess_steps: Record<string, Record<string, unknown>> | null;
  ocr_models: Record<string, Record<string, unknown>> | null;
  enable_llm: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface ProfileCreateRequest {
  name: string;
  description?: string;
  preprocess_steps?: Record<string, Record<string, unknown>>;
  ocr_models?: Record<string, Record<string, unknown>>;
  enable_llm?: boolean;
  is_default?: boolean;
}

export interface ProfileUpdateRequest {
  name?: string;
  description?: string | null;
  preprocess_steps?: Record<string, Record<string, unknown>> | null;
  ocr_models?: Record<string, Record<string, unknown>> | null;
  enable_llm?: boolean;
  is_default?: boolean;
}
```

**File**: `frontend/src/api/client.ts` — add barrel export

### 4.2 Profiles Management Page

**File**: `frontend/src/pages/Profiles.tsx` — new file

Features:
- Table listing all profiles (name, is_default badge, enable_llm, created_at)
- "Set as Default" button per row
- "Edit" button → inline edit modal or dedicated page
- "Delete" button with confirmation
- "Create Profile" button → opens creation form

### 4.3 Profile Editor (Create/Edit)

**File**: `frontend/src/pages/ProfileEditor.tsx` — new file (or inline modal in Profiles.tsx)

This is essentially the QuickRun config panel extracted into a standalone form:
- Name + description text inputs
- Preprocessing steps section (reuse `PreprocessStepCard` components)
- OCR models section (reuse model toggle + param cards from QuickRun)
- LLM toggle checkbox
- "Set as Default" checkbox
- Save / Cancel buttons

### 4.4 Profile Picker on Upload Page

**Modify**: `frontend/src/pages/Upload.tsx`

Add a profile dropdown above the file uploader:
```tsx
<select value={selectedProfileId} onChange={...}>
  <option value="">Default (global config)</option>
  {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
</select>
```
Pass `profile_id` to `createBatch()` and `uploadImages()`.

### 4.5 Profile Picker on Quick Run Page

**Modify**: `frontend/src/pages/QuickRun.tsx`

Add a "Load Profile" dropdown at the top. When selected:
1. Populate `preprocessConfig`, `preprocessEnabled`, `ocrConfig`, `ocrEnabled`, `enableLlm` from the profile
2. Enable the "Custom Preprocessing" and "Custom OCR" toggles
3. User can still override individual settings (inline overrides take precedence)

### 4.6 Routing

**Modify**: `frontend/src/App.tsx`

Add routes:
```tsx
<Route path="/profiles" element={<Profiles />} />
<Route path="/profiles/new" element={<ProfileEditor />} />
<Route path="/profiles/:id/edit" element={<ProfileEditor />} />
```

Add nav entry: "Profiles" under a new "Config" NavGroup (or under History — but Config makes more sense since profiles are reusable settings, not historical data).

**Suggested nav structure**:
```
Dashboard | History ▾ (Runs, Batches, Catalog) | Playground ▾ (Preprocessing, OCR) | Run ▾ (Quick Run, Full Pipeline) | Config ▾ (Profiles)
```

---

## 5. Phase C: Tests

### 5.1 Backend Tests

**File**: `tests/test_api/test_profiles.py` — new file (~15 tests)

| Test | Description |
|---|---|
| `test_create_profile` | POST /profiles with full config |
| `test_create_profile_minimal` | POST with only name (defaults for rest) |
| `test_create_profile_duplicate_name` | 409 on duplicate name |
| `test_list_profiles` | Paginated listing |
| `test_get_profile` | GET by ID |
| `test_get_profile_not_found` | 404 |
| `test_update_profile` | PUT partial update |
| `test_delete_profile` | DELETE |
| `test_delete_profile_not_found` | 404 |
| `test_set_default_profile` | POST /profiles/{id}/set-default unsets previous |
| `test_upload_with_profile` | POST /inputs/upload?profile_id=X stores snapshot |
| `test_batch_with_profile` | POST /batches with profile_id stores snapshot |
| `test_quick_run_with_profile` | POST /run/quick with profile_id loads defaults |
| `test_quick_run_profile_override` | Profile + inline overrides (inline wins) |
| `test_worker_uses_snapshot` | Unit test: worker reads preprocess_config instead of files |

**File**: `tests/test_worker_profile.py` — new file (~5 tests)

| Test | Description |
|---|---|
| `test_worker_profile_snapshot` | Run with snapshot uses it, not global files |
| `test_worker_legacy_fallback` | Run without snapshot falls back to current behavior |
| `test_worker_enable_llm_false` | Snapshot with enable_llm=false skips LLM |
| `test_worker_enable_llm_true` | Snapshot with enable_llm=true runs LLM |
| `test_worker_invalid_snapshot_uses_defaults` | Malformed snapshot falls back gracefully |

### 5.2 Existing Test Updates

- `tests/test_api/conftest.py` — no changes needed (existing monkeypatch covers UPLOAD_DIR)
- `tests/test_worker/test_ocr_worker.py` — update existing tests to assert `preprocess_config` handling
- Tests that create `PipelineRun` via `create_pipeline_run()` — ensure `preprocess_config=None` still works (backward compat)

---

## 6. Implementation Order (Task Breakdown)

### Step 1: DB Model + Migration
- Add `PipelineProfile` to `models.py`
- Create migration `005_add_pipeline_profile.py` (create table + seed default from current files)
- **Verify**: migration runs, model importable

### Step 2: CRUD
- Add 7 CRUD functions to `crud.py`
- **Verify**: unit tests for each CRUD function

### Step 3: Config Snapshot Helper
- Create `services/config.py` with `build_run_config_snapshot()`
- **Verify**: unit test

### Step 4: API Schemas + Routes
- Create `api/schemas/profiles.py`
- Create `api/routes/profiles.py` (6 endpoints)
- Register in `app.py`
- **Verify**: API tests for all endpoints

### Step 5: Wire Profile into Upload + Batch + QuickRun
- Modify `inputs.py` upload endpoint to accept `profile_id`
- Modify `batches.py` create endpoint to accept `profile_id`
- Modify `QuickRunRequest` schema + `run.py` to accept `profile_id`
- **Verify**: API tests for profile-aware upload/batch/quick-run

### Step 6: Worker Reads Snapshot
- Add `_build_model_configs_from_snapshot()` and `_build_preprocess_raw()` helpers
- Modify `_process()` to check `run.preprocess_config` and branch
- Add `enable_llm` parameter to `OCREngine.process()`
- **Verify**: worker tests for snapshot path + legacy fallback

### Step 7: Frontend API Client + Types
- Add types to `api/types.ts`
- Create `api/profiles.ts`
- Update `api/client.ts` barrel
- **Verify**: TypeScript build passes

### Step 8: Frontend Profiles Page
- Create `pages/Profiles.tsx` (list + delete + set-default)
- Create `pages/ProfileEditor.tsx` (create/edit form)
- Add routes to `App.tsx`
- **Verify**: Vite build passes

### Step 9: Frontend Profile Picker
- Add profile dropdown to `Upload.tsx`
- Add profile loader to `QuickRun.tsx`
- **Verify**: Vite build passes, manual test

### Step 10: Full Test Suite + Lint
- Run all 300+ tests
- Run ruff lint
- Run frontend build
- Fix any failures

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Profile JSON shape changes between versions | Old snapshots break | Snapshot is immutable per-run; schema validation at profile creation only |
| `OCREngine.process(enable_llm=)` change breaks callers | QuickRun and playground call `process()` too | Default `enable_llm=True` preserves existing behavior; only worker passes explicit value |
| Migration seed from current config files | Config files may be missing in CI | Seed migration should handle missing/empty files gracefully (empty profile) |
| Profile picker UX complexity | Too many options confuse users | Start simple: dropdown with "Default" option. Inline override is Phase 2 polish. |
| `preprocess_config` column name is misleading | It stores full config now, not just preprocessing | Accept as tech debt. Rename to `config_snapshot` in a future migration if needed. |

---

## 8. Non-Goals (Deferred)

1. **Preprocess presets** (Phase B from earlier discussion) — standalone reusable preprocessing configs. Deferred until profiles are proven useful.
2. **Per-batch config overrides** (beyond profile selection) — not in MVP.
3. **Profile versioning** — profiles are mutable; old runs keep their snapshot.
4. **Profile sharing between users** — single-user system for now.
5. **Renaming `preprocess_config` column** — cosmetic, can be done in a future cleanup migration.
6. **Converging `OCREngine` config assembly** — the god class refactoring is orthogonal and can be done later.
