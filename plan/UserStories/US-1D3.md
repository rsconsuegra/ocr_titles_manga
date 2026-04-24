# US-1D3: Inspect Run Details in UI

**Sub-phase**: 1D — Frontend
**Depends on**: US-1B4 (run detail API), US-1B5 (override API), US-1D2 (navigation from runs page)
**Blocks**: None

---

## Overview

Create the run detail page showing input image preview, per-model OCR results with confidence meters, post-processing results, and a manual override form for corrections.

---

## Implementation Details

### 1. `frontend/src/api/client.ts` additions

```typescript
export interface OCRResultDetail {
  id: string;
  model_name: string;
  raw_text: string;
  confidence: number;
  processing_time_ms: number;
  error: string | null;
  created_at: string;
  post_processing_results: PostProcessingResultDetail[];
}

export interface PostProcessingResultDetail {
  id: string;
  title_en: string | null;
  title_ja: string | null;
  code: string | null;
  confidence: number;
  processing_type: string;
  created_at: string;
}

export interface RunDetailResponse {
  id: string;
  input_image_path: string;
  status: string;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  ocr_results: OCRResultDetail[];
}

export async function getRunDetail(runId: string): Promise<RunDetailResponse> {
  return apiFetch<RunDetailResponse>(`/api/v1/pipeline/runs/${runId}`);
}

export async function overrideResult(
  resultId: string,
  data: { title_en?: string; title_ja?: string; code?: string }
): Promise<PostProcessingResultDetail> {
  return apiFetch<PostProcessingResultDetail>(`/api/v1/results/${resultId}/override`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
```

### 2. `frontend/src/components/ConfidenceMeter.tsx`

Props: `value: number`, `label?: string`

```typescript
function getColor(value: number): string {
  if (value < 0.3) return "bg-red-500";
  if (value < 0.7) return "bg-yellow-500";
  return "bg-green-500";
}
```

Renders: label text + horizontal bar (width = value * 100%) + percentage text. Color-coded per threshold.

### 3. `frontend/src/pages/RunDetail.tsx`

Page layout (vertical sections):

**Header section**:
- Back button (-> `/runs`)
- Run ID (full UUID, copyable)
- Status badge (large)
- Created at / Completed at timestamps
- Error message banner (red) if failed

**Image section**:
- Input image preview (if file exists at `input_image_path`, show `<img>` with API proxy or direct path)

**OCR Results section** (one card per model):
- Model name (bold)
- Raw text (in a `<pre>` block, scrollable if long)
- Confidence meter
- Processing time
- Error message (if any)

**Post-Processing Results section** (within each OCR result card):
- Extracted Title EN
- Extracted Title JA
- Code / ISBN
- Confidence meter
- Processing type badge ("llm", "rules", "llm+rules")

**Override form**:
- Shown below each post-processing result
- Input fields: Title EN, Title JA, Code (pre-filled with current values)
- "Save Override" button
- On success: green "Saved" confirmation, values update in view

State:
```typescript
const [run, setRun] = useState<RunDetailResponse | null>(null);
const [loading, setLoading] = useState(true);
const [editingResult, setEditingResult] = useState<string | null>(null);
const [overrideForm, setOverrideForm] = useState({ title_en: "", title_ja: "", code: "" });
const [saving, setSaving] = useState(false);
```

Data fetching:
```typescript
const { id } = useParams();
useEffect(() => {
  if (id) {
    setLoading(true);
    getRunDetail(id).then(setRun).finally(() => setLoading(false));
  }
}, [id]);
```

Auto-refresh every 5s while status is "pending" or "processing".

---

## Acceptance Criteria

- [ ] `/runs/:id` page renders with run details
- [ ] Status badge color-coded correctly
- [ ] Input image preview displayed
- [ ] Each OCR result shown as a card with model name, raw text, confidence meter
- [ ] Post-processing results nested under their OCR result
- [ ] Confidence meters color-coded: red (<0.3), yellow (0.3-0.7), green (>0.7)
- [ ] Override form pre-fills current values
- [ ] "Save Override" updates values via API and shows confirmation
- [ ] 404 for nonexistent run ID (error message shown)
- [ ] Auto-refreshes while status is active

---

## Expected Views

**Completed run**: Header with green "Completed" badge. Image preview. 1-4 OCR result cards. Each card has: model name, raw text in monospace, confidence bar, extracted data.

**Processing run**: Blue "Processing" badge. Image shown. No results yet. "Processing..." spinner.

**Failed run**: Red "Failed" badge. Error message in red banner. Partial results if any.

**Override form**: Below each post-processing result. Three text inputs (Title EN, Title JA, Code). "Save" button. After save: brief green "Saved!" toast.

---

## Test Specifications

Manual testing checklist:
- [ ] Navigate from runs list to detail: correct run shown
- [ ] Completed run: all sections visible with data
- [ ] Confidence meters show correct colors for different values
- [ ] Override form: edit title, save, value updates
- [ ] Override form: edit code, save, value updates
- [ ] Invalid run ID: error message shown
- [ ] Back button returns to runs list
- [ ] Active run: auto-refreshes (results appear without manual refresh)
