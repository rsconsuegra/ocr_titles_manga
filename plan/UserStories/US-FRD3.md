# US-FRD3: Redesigned Quick Run Page

**Sub-phase**: FR-D — Core Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want the Quick Run page to present a clear upload-configure-results flow so that I can quickly test OCR on a single image with full control over settings.

---

## Scope

### In Scope
- Rewrite QuickRun.tsx with two-column layout
- Collapsible config sections in Card components
- Results area with OcrResultCard and LlmExtractionCard
- Profile loading and YAML import preserved

### Out of Scope
- New OCR models or settings
- Loading states (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/QuickRun.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌──────────────┐ ┌────────────────────────────┐ │
│ │ Image Upload │ │  Configuration              │ │
│ │              │ │  ▼ Preprocessing            │ │
│ │  [preview]   │ │    step configs...          │ │
│ │              │ │  ▼ OCR Models               │ │
│ │  [Upload]    │ │    model configs...         │ │
│ │              │ │  ▼ LLM Settings             │ │
│ │              │ │    LLM config...            │ │
│ │              │ │                              │ │
│ │              │ │  [Run Pipeline]              │ │
│ └──────────────┘ └────────────────────────────┘ │
│                                                  │
│ Results                                          │
│ ┌────────────────────────────────────────────┐   │
│ │ OCR Result / LLM Extraction               │   │
│ └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

Key elements:

**Two-column layout:** `grid grid-cols-5 gap-6`
- Left `col-span-2`: image upload + preview (SingleImageUpload)
- Right `col-span-3`: collapsible config panels

**Collapsible sections:** Each wrapped in Card with clickable header:
```tsx
function CollapsibleSection({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <Card padding="sm" className="mb-4">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between py-2 text-left"
      >
        <span className="font-display font-semibold text-ink">{title}</span>
        <span className="text-sand">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="pt-3 border-t border-linen mt-2">{children}</div>}
    </Card>
  );
}
```

Sections: "Preprocessing", "OCR Models", "LLM Settings"

**Run button:** `<Button variant="primary" size="lg">Run Pipeline</Button>` — prominent position

**Results:** Full-width section below columns, showing OcrResultCard + LlmExtractionCard

**Preserved features:** Profile loading (Select), YAML import (file input + useYamlConfig hook)

---

## Acceptance Criteria

- [ ] Two-column layout: left = image upload/preview, right = config
- [ ] Three collapsible config sections: Preprocessing, OCR Models, LLM Settings
- [ ] Each section has clickable header with expand/collapse toggle
- [ ] "Run Pipeline" Button primary, prominently placed
- [ ] Results appear below both columns after processing
- [ ] Results include OcrResultCard and LlmExtractionCard
- [ ] Profile loading from Select still works
- [ ] YAML config import still works
- [ ] All existing OCR/LLM options preserved

---

## Validation

1. Screenshot QuickRun — verify two-column layout with image area left, config panels right
2. Click each config section header — verify collapse/expand
3. Load a profile — verify config populates
4. Upload image + run — verify results appear below
