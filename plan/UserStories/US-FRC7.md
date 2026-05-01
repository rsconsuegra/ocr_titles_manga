# US-FRC7: Complete DSO Component Removal

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRC1–C6 (all new ui/ components exist)
**Blocks**: US-FRD1–D5 (core pages), US-FRE1–E8 (secondary pages), US-FRF5 (final cleanup)

---

## Story

> As a user, I want all neumorphic/oscilloscope components removed from the codebase so that the app has a single, consistent visual language.

---

## Scope

### In Scope
- Delete `frontend/src/components/dso/` directory (11 files)
- Update ALL imports across all pages and shared components
- Replace every DsoButton/DsoCard/DsoBadge/etc. with new ui/ equivalents
- Verify build succeeds with zero TypeScript errors

### Out of Scope
- Redesigning page layouts (FR-D, FR-E)
- Adding new features

---

## Implementation Details

### 1. Delete DSO directory

```bash
rm -rf frontend/src/components/dso/
```

11 files removed:
- DsoButton.tsx, DsoCard.tsx, DsoBadge.tsx, DsoInput.tsx, DsoSelect.tsx
- DsoTable.tsx, DsoPagination.tsx, DsoProgressBar.tsx, DsoErrorBanner.tsx
- DsoBrandStrip.tsx, index.ts

### 2. Create barrel export

`frontend/src/components/ui/index.ts`:
```ts
export { default as Button } from "./Button";
export { default as Card } from "./Card";
export { default as Badge } from "./Badge";
export { default as Input } from "./Input";
export { default as Select } from "./Select";
export { default as Table } from "./Table";
export { default as Pagination } from "./Pagination";
export { default as ProgressBar } from "./ProgressBar";
export { default as ErrorBanner } from "./ErrorBanner";
export { default as EmptyState } from "./EmptyState";
```

### 3. Import replacement mapping

Every file in `frontend/src/` that imports from `components/dso/` must be updated:

| Old Import | New Import |
|------------|------------|
| `DsoButton` from `../dso` or `./dso` | `Button` from `../ui` or `./ui` |
| `DsoCard` | `Card` |
| `DsoBadge` | `Badge` |
| `DsoInput` | `Input` |
| `DsoSelect` | `Select` |
| `DsoTable` | `Table` |
| `DsoPagination` | `Pagination` |
| `DsoProgressBar` | `ProgressBar` |
| `DsoErrorBanner` | `ErrorBanner` |
| `DsoBrandStrip` | (removed — replaced by Sidebar/TopBar) |
| `DsoScrew` | (removed — decorative, no replacement) |
| `DsoVentGrille` | (removed — decorative, no replacement) |

### 4. Component prop migration

| DSO Component | DSO Props | New Component | New Props |
|---------------|-----------|---------------|-----------|
| `DsoButton variant="primary"` | primary, secondary, amber, danger, ghost | `Button variant="primary"` | primary, secondary, danger, ghost (amber → secondary) |
| `DsoCard variant="flat"` | flat, inset, lcd | `Card` | no variant prop; accent, padding, hover |
| `DsoBadge variant="completed"` | 7 variant strings | `Badge status="completed"` | `status` prop instead of `variant` |
| `DsoInput` | label, value, onChange, ... | `Input` | same API |
| `DsoSelect` | label, options, ... | `Select` | options: `{value, label}[]` |
| `DsoTable columns={[...]}` | DsoTh/DsoTd sub-components | `Table columns={[...]}` | Column-based API (no sub-components) |
| `DsoPagination` | offset, limit, total, onPrev, onNext | `Pagination` | same API |
| `DsoProgressBar value={n}` | value, size | `ProgressBar` | value, size, showLabel |

### 5. Files requiring import updates

**Pages (13 files):**
- Dashboard.tsx, Runs.tsx, RunDetail.tsx, BatchRuns.tsx, BatchRunDetail.tsx
- Catalog.tsx, OcrPlayground.tsx, PreprocessPlayground.tsx, QuickRun.tsx
- Upload.tsx, Profiles.tsx, ProfileEditor.tsx, Settings.tsx

**Shared components (~7 files):**
- RunStatusBadge.tsx (DsoBadge → Badge)
- ConfidenceMeter.tsx (DsoProgressBar → ProgressBar)
- PreprocessStepCard.tsx (DsoCard, DsoInput, DsoSelect → Card, Input, Select)
- OcrModelCard.tsx (DsoCard → Card)
- OcrResultCard.tsx (DsoCard → Card)
- LlmConfigSection.tsx (DsoCard, DsoSelect → Card, Select)
- PromptSettingsPanel.tsx (DsoCard, DsoInput → Card, Input)
- LlmExtractionCard.tsx (DsoCard → Card)

**Note:** App.tsx was already cleaned in US-FRB3 (no DSO imports remain).

### 6. DsoCard variant → Card mapping

Since DsoCard had 3 visual variants (flat=neo-panel, inset=deep-inset, lcd=lcd-screen), the replacement is contextual:

| DsoCard Usage | Replacement |
|---------------|-------------|
| `<DsoCard variant="flat">` | `<Card>` (default snow card) |
| `<DsoCard variant="inset">` | `<Card className="bg-cream">` (subtle inset feel) |
| `<DsoCard variant="lcd">` | `<Card>` (LCD-specific styling removed) |

---

## Acceptance Criteria

- [ ] `frontend/src/components/dso/` directory does not exist
- [ ] Zero files import from `components/dso/` or `./dso/`
- [ ] All 13 page files import from `components/ui/`
- [ ] All shared component files import from `components/ui/`
- [ ] `DsoButton` → `Button` everywhere
- [ ] `DsoCard` → `Card` everywhere
- [ ] `DsoBadge` → `Badge` with `status` prop
- [ ] `DsoInput`/`DsoSelect` → `Input`/`Select`
- [ ] `DsoTable` → `Table` with columns API
- [ ] `DsoPagination`/`DsoProgressBar`/`DsoErrorBanner` → new equivalents
- [ ] `DsoBrandStrip`/`DsoScrew`/`DsoVentGrille` removed entirely
- [ ] `npm run build` succeeds with zero TypeScript errors
- [ ] No runtime errors on any page

---

## Validation

1. `cd frontend && npm run build` — zero errors
2. Grep `frontend/src/` for `"dso"` or `"Dso"` — zero matches in imports
3. Open each route in browser — verify no white screen or console errors
4. Take screenshots of 3 representative pages for visual check
