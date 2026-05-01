# US-FRE5: Redesigned Preprocess Playground

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want the preprocess playground to show a clear step pipeline with before/after comparison so that I can tune preprocessing settings visually.

---

## Scope

### In Scope
- Rewrite PreprocessPlayground.tsx with step pipeline bar + ImageCompare
- Active step highlighting
- Preview and export buttons

### Out of Scope
- New preprocessing steps
- Loading states (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/PreprocessPlayground.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌──────────────────────┐ ┌────────────────────┐ │
│ │ Upload Image         │ │ Before / After     │ │
│ │ [dropzone]           │ │ ┌───────┬────────┐ │ │
│ │                      │ │ │Before │ After  │ │ │
│ │ Step Pipeline:       │ │ │       │        │ │ │
│ │ [●]─[●]─[●]─[●]─[●]│ │ │       │        │ │ │
│ │  ROI GrU Dn Bz      │ │ └───────┴────────┘ │ │
│ │                      │ └────────────────────┘ │
│ │ Step Config:         │                         │
│ │ ┌──────────────────┐ │                         │
│ │ │ ROI Settings     │ │                         │
│ │ │ method: [select] │ │                         │
│ │ │ padding: [___]   │ │                         │
│ │ └──────────────────┘ │                         │
│ │                      │                         │
│ │ [Preview] [Pipeline] │                         │
│ │ [Export Config]      │                         │
│ └──────────────────────┘                         │
└─────────────────────────────────────────────────┘
```

**Step pipeline bar:**
```tsx
<div className="flex items-center gap-1 mb-6">
  {steps.map((step, i) => (
    <Fragment key={step.name}>
      <button
        onClick={() => setActiveStep(step.name)}
        className={`
          flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-body font-medium transition-colors
          ${activeStep === step.name
            ? "bg-indigo text-snow"
            : "bg-linen text-charcoal hover:bg-cream"}
        `}
      >
        {step.display_name}
      </button>
      {i < steps.length - 1 && <span className="text-sand">→</span>}
    </Fragment>
  ))}
</div>
```

**ImageCompare:** Right panel shows side-by-side before/after using existing ImageCompare component

**Step config:** PreprocessStepCard component instances for the active step

**Buttons:** "Preview" Button primary, "Preview Pipeline" Button secondary, "Export Config" Button ghost

---

## Acceptance Criteria

- [ ] Left side: image upload + horizontal step pipeline bar
- [ ] Right side: ImageCompare before/after view
- [ ] Step config shown below pipeline bar using PreprocessStepCard
- [ ] Active step highlighted with indigo background in pipeline bar
- [ ] Inactive steps show linen background
- [ ] Arrows between steps in pipeline bar
- [ ] "Preview" Button primary triggers single-step preview
- [ ] "Preview Pipeline" Button secondary triggers full pipeline preview
- [ ] "Export Config" Button ghost exports YAML

---

## Validation

1. Screenshot Preprocess Playground — verify step pipeline bar and ImageCompare layout
2. Click different steps — verify active highlighting changes
3. Click Preview — verify before/after comparison updates
