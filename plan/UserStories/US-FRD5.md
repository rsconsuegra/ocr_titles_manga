# US-FRD5: Redesigned Run Detail Page

**Sub-phase**: FR-D — Core Pages
**Depends on**: US-FRC7 (DSO removed, new components), US-FRB2 (TopBar actions)
**Blocks**: None

---

## Story

> As a user, I want a two-column run detail page with the image on the left and results on the right so that I can see the source image alongside OCR output.

---

## Scope

### In Scope
- Rewrite RunDetail.tsx with two-column layout
- Image preview from API
- Run metadata card with status Badge
- Collapsible OCR result cards
- Post-processing result with LlmExtractionCard
- Override form for title_en, title_ja, code
- TopBar action buttons (Retry, Cancel)

### Out of Scope
- Loading skeletons (US-FRF1)
- WebSocket live updates

---

## Implementation Details

### 1. `frontend/src/pages/RunDetail.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ TopBar: [Run Detail]          [Retry] [Cancel]  │
├─────────────────────────────────────────────────┤
│ ┌────────────┐ ┌──────────────────────────────┐ │
│ │ Image      │ │  Run Metadata                │ │
│ │ Preview    │ │  Status: [Completed]          │ │
│ │            │ │  Created: 2m ago              │ │
│ │            │ │  Completed: 1m ago            │ │
│ │            │ ├──────────────────────────────┤ │
│ │            │ │  OCR: PaddleOCR ▼            │ │
│ │            │ │  Raw text...                  │ │
│ │            │ │  Confidence: 87%              │ │
│ │            │ ├──────────────────────────────┤ │
│ │            │ │  LLM Extraction               │ │
│ │            │ │  title_en: "One Piece"        │ │
│ │            │ │  title_ja: "ワンピース"         │ │
│ │            │ │  code: "OP-001"               │ │
│ │            │ ├──────────────────────────────┤ │
│ │            │ │  Override                     │ │
│ │            │ │  title_en: [___________]      │ │
│ │            │ │  title_ja: [___________]      │ │
│ │            │ │  code:     [___________]      │ │
│ │            │ │  [Save Override]              │ │
│ └────────────┘ └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Two-column layout:** `grid grid-cols-5 gap-6`
- Left `col-span-2`: large image preview
- Right `col-span-3`: metadata + results + override form

**Image preview:**
```tsx
<Card>
  <img
    src={`/api/v1/pipeline/runs/${runId}/image`}
    alt="Input"
    className="w-full rounded-md"
  />
</Card>
```

**Metadata card:**
```tsx
<Card>
  <div className="space-y-3">
    <div className="flex items-center gap-3">
      <span className="label-text">Status</span>
      <Badge status={run.status} />
    </div>
    <div>
      <span className="label-text">Created</span>
      <p className="text-sm text-charcoal font-body">{formatDate(run.created_at)}</p>
    </div>
    {run.completed_at && (
      <div>
        <span className="label-text">Completed</span>
        <p className="text-sm text-charcoal font-body">{formatDate(run.completed_at)}</p>
      </div>
    )}
  </div>
</Card>
```

**OCR results:** Collapsible Card per model:
```tsx
{run.ocr_results?.map((result) => (
  <Card key={result.id} padding="sm">
    <button onClick={() => toggleResult(result.id)} className="w-full flex justify-between">
      <span className="font-display font-semibold text-ink">{result.model_name}</span>
      <span className="text-sand">{expanded[result.id] ? "−" : "+"}</span>
    </button>
    {expanded[result.id] && (
      <div className="pt-3 border-t border-linen mt-2">
        <p className="text-sm text-charcoal font-body whitespace-pre-wrap">{result.raw_text}</p>
        <ConfidenceMeter value={result.confidence * 100} />
      </div>
    )}
  </Card>
))}
```

**Override form:**
```tsx
<Card>
  <Card.Header title="Override" />
  <div className="space-y-3">
    <Input label="Title (EN)" value={override.title_en} onChange={...} />
    <Input label="Title (JA)" value={override.title_ja} onChange={...} />
    <Input label="Code" value={override.code} onChange={...} />
    <Button variant="primary" onClick={handleSaveOverride}>Save Override</Button>
  </div>
</Card>
```

**TopBar actions:** Need to pass actions to TopBar via context or layout wrapper:
- "Retry" Button secondary — shown when status is "failed" or "completed"
- "Cancel" Button ghost — shown when status is "pending" or "processing"

---

## Acceptance Criteria

- [ ] Two-column layout: left (40%) = image, right (60%) = results
- [ ] Image loads from `/api/v1/pipeline/runs/{id}/image`
- [ ] Metadata card shows status Badge + timestamps
- [ ] OCR results shown as collapsible cards per model (model name, raw text, confidence)
- [ ] Post-processing result shown in LlmExtractionCard
- [ ] Override form with Input fields for title_en, title_ja, code + Save Button
- [ ] Override calls `PUT /api/v1/results/{result_id}/override` API
- [ ] TopBar shows "Retry" button when run is failed/completed
- [ ] TopBar shows "Cancel" button when run is pending/processing
- [ ] All timestamps formatted in human-readable form

---

## Validation

1. Screenshot RunDetail — verify two-column layout with image left
2. Expand an OCR result card — verify raw text and confidence
3. Edit override fields + click Save — verify API call
4. Verify TopBar shows correct action buttons based on run status
