# US-1D1: Upload Images via Web UI

**Sub-phase**: 1D — Frontend
**Depends on**: US-1B1 (upload API), US-1B2 (trigger API), Step 15 (Frontend Setup)
**Blocks**: None

---

## Overview

Create the frontend upload page with drag-and-drop image upload, preview thumbnails, and pipeline trigger functionality. This is the primary entry point for operators to submit images for OCR processing.

---

## Implementation Details

### 1. `frontend/src/api/client.ts`

HTTP client wrapping `fetch`:

```typescript
const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export async function uploadImages(files: File[]): Promise<PipelineRunResponse[]> {
  const formData = new FormData();
  files.forEach(f => formData.append("files", f));
  return apiFetch<PipelineRunResponse[]>("/api/v1/inputs/upload", {
    method: "POST",
    body: formData,
  });
}

export async function triggerPipeline(runId: string): Promise<{ message: string; run_id: string }> {
  return apiFetch("/api/v1/pipeline/run/" + runId, { method: "POST" });
}

export interface PipelineRunResponse {
  id: string;
  input_image_path: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}
```

### 2. `frontend/src/components/ImageUploader.tsx`

Props: `onFilesSelected: (files: File[]) => void`, `maxFiles?: number`

Behavior:
- Drag-and-drop zone with dashed border
- File picker button as fallback
- Shows thumbnail previews (using `URL.createObjectURL`)
- Validates file types: `.png, .jpg, .jpeg, .webp, .tiff, .tif, .bmp`
- Validates max 10 files
- Shows file name and size per preview
- Remove button per preview

State:
```typescript
const [files, setFiles] = useState<File[]>([]);
const [dragActive, setDragActive] = useState(false);
const [errors, setErrors] = useState<string[]>([]);
```

### 3. `frontend/src/pages/Upload.tsx`

Page layout:
- Title: "Upload Manga Images"
- `ImageUploader` component
- Submit button: "Upload & Process"
- After upload: show list of created runs in a table
  - Column: Run ID (truncated), Image, Status badge, "Trigger Pipeline" button
- Each "Trigger Pipeline" button calls `triggerPipeline(runId)`
- After trigger: button changes to "Processing..." (disabled), status badge updates to blue
- Error messages shown in red banner

State:
```typescript
const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
const [uploading, setUploading] = useState(false);
const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
const [triggeredRuns, setTriggeredRuns] = useState<Set<string>>(new Set());
const [error, setError] = useState<string | null>(null);
```

Flow:
1. User selects/drops files -> previews shown
2. Click "Upload & Process" -> `uploadImages(files)` -> set runs
3. For each run, click "Trigger Pipeline" -> `triggerPipeline(run.id)` -> mark triggered
4. Error states shown in red banner

---

## Acceptance Criteria

- [ ] `/upload` page renders with drag-and-drop zone
- [ ] Dropping 1-10 valid images shows previews
- [ ] Invalid file types (e.g., .gif) rejected with error message
- [ ] More than 10 files rejected with error message
- [ ] "Upload & Process" sends files to API, shows created runs
- [ ] Each run has "Trigger Pipeline" button
- [ ] Clicking "Trigger Pipeline" calls API, button changes to "Processing..."
- [ ] API errors shown as red banner messages
- [ ] Empty state shows placeholder text when no files selected

---

## Expected Views

**Initial state**: Centered drag-and-drop zone with text "Drop manga images here or click to browse". Dashed border, icon.

**With files selected**: Grid of thumbnail previews (4 per row), each with file name, size, and X button. "Upload & Process" button at bottom.

**After upload**: Table with columns: #, Image Preview, Run ID (first 8 chars), Status Badge, Action Button.

**After trigger**: Button changes to "Processing..." (blue, disabled). Status badge = blue "processing".

---

## Test Specifications

Manual testing checklist:
- [ ] Drag single PNG -> preview shown -> upload succeeds -> run appears
- [ ] Drag 3 images -> all previews shown -> upload -> 3 runs appear
- [ ] Drag .gif file -> error message shown
- [ ] Drag 11 files -> error message shown
- [ ] Click trigger -> button state changes
- [ ] API error (server down) -> red banner shown
