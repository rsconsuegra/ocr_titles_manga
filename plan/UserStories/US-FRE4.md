# US-FRE4: Redesigned OCR Playground

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want the OCR playground to have a clean two-panel layout so that I can configure and run OCR tests efficiently.

---

## Scope

### In Scope
- Rewrite OcrPlayground.tsx with two-panel layout
- Radio-style model selection cards
- Collapsible LLM config section
- Results panel with OcrResultCard + LlmExtractionCard

### Out of Scope
- New OCR models
- Loading states (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/OcrPlayground.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌──────────────────┐ ┌─────────────────────────┐│
│ │ Upload Image     │ │ Results                 ││
│ │ [dropzone]       │ │                         ││
│ │                  │ │ OCR Result:             ││
│ │ Select Model     │ │ PaddleOCR - 92% conf    ││
│ │ ┌──────────────┐ │ │ Raw text...             ││
│ │ │● PaddleOCR   │ │ │                         ││
│ │ │○ Tesseract   │ │ │ LLM Extraction:         ││
│ │ │○ EasyOCR     │ │ │ title_en: "One Piece"   ││
│ │ └──────────────┘ │ │ title_ja: "ワンピース"    ││
│ │                  │ │ code: "OP-001"          ││
│ │ ▼ LLM Settings   │ │                         ││
│ │   [config...]    │ │                         ││
│ │                  │ │                         ││
│ │ [Run OCR]        │ │                         ││
│ └──────────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**Two-panel layout:** `grid grid-cols-2 gap-6`

**Model selection — radio-style cards:**
```tsx
{models.map((model) => (
  <Card
    key={model.name}
    padding="sm"
    accent={selectedModel === model.name ? "indigo" : undefined}
    className={`cursor-pointer ${selectedModel === model.name ? "ring-2 ring-indigo/20" : ""}`}
    onClick={() => setSelectedModel(model.name)}
  >
    <div className="flex items-center gap-3">
      <div className={`w-4 h-4 rounded-full border-2 ${
        selectedModel === model.name ? "border-indigo bg-indigo" : "border-linen"
      }`} />
      <div>
        <p className="font-body font-medium text-charcoal">{model.display_name}</p>
        <p className="text-xs text-sand font-body">{model.description}</p>
      </div>
    </div>
  </Card>
))}
```

**LLM config:** Collapsible section using LlmConfigSection component

**"Run OCR":** `<Button variant="primary" size="lg">Run OCR</Button>` — triggers API call

**Results:** Right panel shows OcrResultCard + LlmExtractionCard after OCR completes

---

## Acceptance Criteria

- [ ] Two-panel layout: left = upload + config, right = results
- [ ] Model selection uses Card components with indigo accent on selected model
- [ ] Selected model shows filled radio dot + indigo border
- [ ] LLM config section is collapsible via LlmConfigSection
- [ ] "Run OCR" Button primary triggers OCR API call
- [ ] Results show OcrResultCard and LlmExtractionCard
- [ ] All model and LLM options preserved from current implementation

---

## Validation

1. Screenshot OCR Playground — verify two-panel layout
2. Click different model cards — verify selection highlight changes
3. Run OCR — verify results appear in right panel
