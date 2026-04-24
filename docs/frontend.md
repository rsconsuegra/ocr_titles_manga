# Frontend Reference

## Tech Stack

| Technology | Version |
|---|---|
| React | 19 |
| TypeScript | 5 |
| Vite | 6 |
| Tailwind CSS | 4 |
| React Router | 7 |

---

## Directory Structure

```
frontend/src/
├── api/                      # API client layer
│   ├── types.ts              # All TypeScript interfaces
│   ├── client.ts             # Barrel exports
│   ├── pipeline.ts           # Upload, trigger, list runs
│   ├── batch.ts              # Batch CRUD
│   ├── profiles.ts           # Profile CRUD
│   ├── catalog.ts            # Catalog CRUD
│   ├── ocr.ts                # OCR model registry + run
│   ├── preprocess.ts         # Step descriptors + preview
│   └── run.ts                # Quick run
├── components/               # Reusable UI components
│   ├── ConfidenceMeter.tsx   # Visual confidence bar
│   ├── ImageCompare.tsx      # Side-by-side image comparison
│   ├── ImageUploader.tsx     # Drag-and-drop file upload
│   ├── PipelineFilmstrip.tsx # Horizontal step result display
│   ├── PreprocessStepCard.tsx# Config card for steps/models
│   └── RunStatusBadge.tsx    # Status badge with colors
├── hooks/                    # Custom React hooks
│   ├── useFileReader.ts      # Reads File → base64 data URL
│   └── useYamlConfig.ts      # Parses YAML → config + enabled dicts
├── pages/                    # Route-level page components
│   ├── Dashboard.tsx         # Home / overview
│   ├── Runs.tsx              # Paginated pipeline run list
│   ├── RunDetail.tsx         # Single run detail with OCR results
│   ├── BatchRuns.tsx         # Batch list with progress bars
│   ├── BatchRunDetail.tsx    # Batch detail + process all + auto-poll
│   ├── Catalog.tsx           # Catalog entries with search
│   ├── Upload.tsx            # Image upload + batch/profile picker
│   ├── QuickRun.tsx          # Stateless pipeline with config UI
│   ├── OcrPlayground.tsx     # Single model OCR testing
│   ├── PreprocessPlayground.tsx # Step-by-step preprocessing
│   ├── Profiles.tsx          # Profile list management
│   └── ProfileEditor.tsx     # Profile create/edit form
├── App.tsx                   # Router + navigation
├── main.tsx                  # Entry point
└── index.css                 # Tailwind imports
```

---

## Routing

Defined in `App.tsx` using React Router v7 `<BrowserRouter>`:

| Path | Component | Description |
|---|---|---|
| `/` | `Dashboard` | Home overview |
| `/runs` | `Runs` | Pipeline run list |
| `/runs/:id` | `RunDetail` | Single run detail |
| `/batches` | `BatchRuns` | Batch list |
| `/batches/:id` | `BatchRunDetail` | Batch detail with runs |
| `/catalog` | `Catalog` | Catalog entries |
| `/run/quick` | `QuickRun` | Stateless pipeline |
| `/run/pipeline` | `Upload` | Upload + trigger |
| `/upload` | `Upload` | Alias |
| `/playground/preprocess` | `PreprocessPlayground` | Preprocessing UI |
| `/playground/ocr` | `OcrPlayground` | OCR model testing |
| `/profiles` | `Profiles` | Profile list |
| `/profiles/new` | `ProfileEditor` | Create profile |
| `/profiles/:id/edit` | `ProfileEditor` | Edit profile |
| `/preprocess` | `PreprocessPlayground` | Alias |

---

## Navigation

Four navigation groups with dropdown menus:

```
Dashboard | History ▾ | Playground ▾ | Run ▾ | Config ▾
```

- **History**: Runs, Batches, Catalog
- **Playground**: Preprocessing, OCR
- **Run**: Quick Run, Full Pipeline
- **Config**: Profiles

---

## API Client

All API calls go through domain-specific modules in `api/`. The base URL is `http://localhost:8000/api/v1` (configured via Vite proxy in development).

### `api/pipeline.ts`

| Function | Method | Endpoint |
|---|---|---|
| `uploadImages(files, profileId?)` | POST multipart | `/inputs/upload?profile_id=...` |
| `triggerPipeline(runId)` | POST | `/pipeline/run/{runId}` |
| `listRuns(status?, limit?, offset?)` | GET | `/pipeline/runs` |
| `getRunDetail(runId)` | GET | `/pipeline/runs/{runId}` |

### `api/batch.ts`

| Function | Method | Endpoint |
|---|---|---|
| `createBatch(files, name?, profileId?)` | POST form | `/batches` |
| `triggerBatch(batchId)` | POST | `/batches/{id}/trigger` |
| `listBatches(status?, limit?, offset?)` | GET | `/batches` |
| `getBatchDetail(batchId)` | GET | `/batches/{id}` |

### `api/profiles.ts`

| Function | Method | Endpoint |
|---|---|---|
| `listProfiles(limit?, offset?)` | GET | `/profiles` |
| `getProfile(id)` | GET | `/profiles/{id}` |
| `createProfile(data)` | POST | `/profiles` |
| `updateProfile(id, data)` | PUT | `/profiles/{id}` |
| `deleteProfile(id)` | DELETE | `/profiles/{id}` |
| `setDefaultProfile(id)` | POST | `/profiles/{id}/set-default` |

### `api/catalog.ts`

| Function | Method | Endpoint |
|---|---|---|
| `listCatalog(status?, search?, limit?, offset?)` | GET | `/catalog` |
| `getCatalogEntry(id)` | GET | `/catalog/{id}` |
| `updateCatalogEntry(id, data)` | PUT | `/catalog/{id}` |
| `exportCatalog()` | GET | `/catalog/export` |

### `api/ocr.ts`

| Function | Method | Endpoint |
|---|---|---|
| `getOCRModels()` | GET | `/ocr/registry` |
| `runOCR(image, modelName, params?, enableLlm?)` | POST | `/ocr/run` |
| `exportOCRConfig(models)` | POST | `/ocr/export` |

### `api/preprocess.ts`

| Function | Method | Endpoint |
|---|---|---|
| `getPreprocessSteps()` | GET | `/preprocess/steps` |
| `previewStep(image, stepName, params)` | POST | `/preprocess/preview/step` |
| `previewPipeline(image, steps)` | POST | `/preprocess/preview/pipeline` |
| `exportPipeline(steps)` | POST | `/preprocess/export` |

### `api/run.ts`

| Function | Method | Endpoint |
|---|---|---|
| `quickRun(image, options?)` | POST | `/run/quick` |

---

## Key Types (`api/types.ts`)

| Type | Purpose |
|---|---|
| `PipelineRunResponse` | Run summary (id, status, timestamps) |
| `RunDetailResponse` | Run with nested OCR + post-processing results |
| `PaginatedResponse<T>` | Paginated list wrapper |
| `BatchRunResponse` | Batch summary with progress counters |
| `BatchRunDetailResponse` | Batch with nested runs |
| `ProfileResponse` | Profile with full config |
| `ProfileCreateRequest` | Profile creation payload |
| `ProfileUpdateRequest` | Partial profile update |
| `CatalogEntryResponse` | Catalog entry with status |
| `ModelDescriptorResponse` | OCR model with params, availability, enabled |
| `OCRResultData` | OCR output from a single model |
| `LLMResultData` | LLM extraction result |
| `QuickRunResponse` | Quick run output |
| `StepDescriptor` | Preprocessing step definition |
| `ParamDescriptor` | Step/model parameter definition |
| `PreviewStepResponse` | Single step preview result |
| `PreviewPipelineResponse` | Full pipeline preview result |

---

## Components

### `ImageUploader`

Drag-and-drop file input. Validates extensions client-side (`.png`, `.jpg`, `.jpeg`, `.webp`, `.tiff`, `.tif`, `.bmp`). Max 10 files. Calls `onFilesSelected(files: File[])` prop.

### `PreprocessStepCard`

Dual-purpose card used for both preprocessing steps and OCR model params. Renders parameter inputs based on `ParamDescriptor.type`:
- `text` → text input
- `number` → number input (with min/max/step)
- `select` → dropdown
- `boolean` → checkbox
- `multiselect` → multi-select checkboxes

Props: `step`, `params`, `enabled`, `onParamsChange`, `onEnabledChange`, `showEnabled`

### `ConfidenceMeter`

Visual progress bar for confidence values (0.0–1.0). Color-coded:
- Green (> 0.7)
- Yellow (0.4–0.7)
- Red (< 0.4)

### `RunStatusBadge`

Colored badge for run/batch statuses:
- `pending` → gray
- `processing` → blue (pulsing)
- `completed` → green
- `failed` → red
- `partial_failure` → orange

### `ImageCompare`

Side-by-side image comparison slider. Used in preprocessing playground.

### `PipelineFilmstrip`

Horizontal strip showing the output of each preprocessing step with timing.

---

## Hooks

### `useFileReader`

```typescript
const readFile = useFileReader();
const dataUrl = await readFile(file); // returns base64 data URL
```

Wraps `FileReader.readAsDataURL` in a Promise.

### `useYamlConfig`

```typescript
const parseYaml = useYamlConfig();
const { config, enabled } = parseYaml(yamlString, "preprocessing" | "models");
```

Parses a YAML string and extracts config dicts + enabled booleans for each step/model. Used in QuickRun for YAML config upload.

---

## Key Pages

### Upload (`pages/Upload.tsx`)

- ImageUploader for file selection
- Profile dropdown (loads from `listProfiles()`)
- Two action buttons: "Upload Individually" (creates separate runs) and "Create Batch" (creates batch + runs)
- Both pass the selected `profileId` to the API

### QuickRun (`pages/QuickRun.tsx`)

- Image upload with preview
- Profile dropdown — loads profile config into UI state
- Custom Preprocessing toggle (with per-step cards)
- Custom OCR Models toggle (with per-model cards)
- LLM toggle
- YAML upload for both preprocessing and OCR configs
- Results panel showing OCR output + LLM extraction

### BatchRunDetail (`pages/BatchRunDetail.tsx`)

- Stats cards (total, completed, failed)
- Progress bar
- "Process All" button to trigger the batch
- Runs table with status badges
- **Auto-polling**: Refreshes every 3 seconds while status is `processing`

### ProfileEditor (`pages/ProfileEditor.tsx`)

- Used for both create and edit (detects `:id` route param)
- Name, description inputs
- Preprocessing section: iterates `STEP_ORDER`, renders `PreprocessStepCard` for each
- OCR Models section: iterates models, renders toggle + params
- LLM toggle
- Default profile checkbox
- Save / Cancel buttons
