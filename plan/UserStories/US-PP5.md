# US-PP5: Interactive Parameter Configuration

**Feature**: Preprocessing Playground
**Depends on**: US-PP1 (step registry provides param schemas)
**Blocks**: None (frontend-only, enhances US-PP2/PP3)

---

## Overview

Create dynamic parameter forms rendered from the step descriptor schemas returned by the API. Each parameter type maps to an appropriate UI control: dropdowns for enums, sliders for numeric ranges, and toggles for booleans. This ensures the playground UI is entirely data-driven from the registry.

---

## Implementation Details

### 1. `frontend/src/components/PreprocessStepCard.tsx` (new)

Expandable accordion component for a single preprocessing step.

**Props**:
```typescript
interface PreprocessStepCardProps {
    step: StepDescriptor;
    onPreview: (stepName: string, config: Record<string, any>) => void;
    onAddToPipeline: (stepName: string, config: Record<string, any>) => void;
    isExpanded: boolean;
    onToggle: () => void;
    pipelineEnabled: boolean;
    onTogglePipeline: (enabled: boolean) => void;
}
```

**Parameter rendering logic**:
- `type === "select"` → `<select>` element with `<option>` for each item in `options`
- `type === "int"` or `type === "float"` → `<input type="range">` with `min`, `max`, `step` from descriptor + numeric readout display
- `type === "bool"` → Toggle switch (checkbox styled as toggle)

**State**: Local state holds current param values, initialized from `descriptor.params[name].default`.

**Actions**:
- **Preview** button → calls `onPreview(step.name, currentConfig)`
- **Add to Pipeline** button → calls `onAddToPipeline(step.name, currentConfig)` + toggles pipeline on

### 2. `frontend/src/pages/PreprocessPlayground.tsx` (relevant section)

Step toolbox section:
- Fetches steps from `GET /api/v1/preprocess/steps` on mount
- Renders one `PreprocessStepCard` per step
- Only one card expanded at a time (accordion pattern)
- Expanded card is visually highlighted (left border accent or bg tint)

---

## Acceptance Criteria

- [ ] Parameter forms render dynamically from step descriptor data
- [ ] `select` params render as dropdown menus with all options listed
- [ ] `int`/`float` params render as range sliders with min, max, step from descriptor
- [ ] Range sliders show current numeric value as a readout
- [ ] `bool` params render as toggle switches
- [ ] Default values are pre-populated from the descriptor
- [ ] Changing a parameter value updates the local state
- [ ] "Preview" button sends current parameter values to the API
- [ ] "Add to Pipeline" copies current params to pipeline config and enables the step
- [ ] Step cards expand/collapse in accordion pattern (one open at a time)
- [ ] Currently expanded step is visually distinct from collapsed steps
- [ ] All 5 steps render correctly with their specific parameter types
