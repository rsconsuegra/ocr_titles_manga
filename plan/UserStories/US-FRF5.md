# US-FRF5: No DSO Remnants

**Sub-phase**: FR-F — Polish (Final)
**Depends on**: ALL previous user stories (FR-A through FR-F4)
**Blocks**: None (this is the final story)

---

## Story

> As a user, I want zero visual or code remnants of the old oscilloscope/DSO design so that the app feels completely redesigned.

---

## Scope

### In Scope
- Grep entire `frontend/src/` for any remaining DSO references
- Remove all found references
- Verify `npm run build`, `make frontend-lint`, `make frontend-format` all pass
- Visual audit via screenshot + MCP vision analysis

### Out of Scope
- New features
- Backend changes

---

## Implementation Details

### 1. Grep audit checklist

Search `frontend/src/` for each of these terms. Every match must be removed or justified:

**DSO component names:**
- `DsoButton`, `DsoCard`, `DsoBadge`, `DsoInput`, `DsoSelect`
- `DsoTable`, `DsoTh`, `DsoTd`, `DsoPagination`, `DsoProgressBar`
- `DsoErrorBanner`, `DsoBrandStrip`, `DsoScrew`, `DsoVentGrille`

**DSO import paths:**
- `components/dso`, `./dso`, `../dso`

**DSO CSS class names:**
- `neo-panel`, `neo-inset`, `neo-deep-inset`, `lcd-screen`, `lcd-graticule`
- `led`, `led-active`, `led-amber`, `led-off`
- `tech-label`, `tech-label-bright`
- `breathing`, `haptic-snap`, `neo-press`

**DSO color tokens:**
- `chassis`, `panel`, `lcd`, `teal`, `amber`, `bright`, `muted`
- `highlight`, `panel-light`, `surface-dark`, `teal-dim`, `teal-glow`
- `amber-dim`, `amber-glow`

**DSO font tokens:**
- `font-tech`

**DSO jargon text:**
- "OSCILLOSCOPE", "TACTICAL", "SERVICE MATRIX", "OSC CONTROL"
- "DSO", "Digital Storage Oscilloscope"

### 2. Cleanup commands

```bash
# Search for any remaining DSO references
cd frontend/src && grep -r "Dso" --include="*.tsx" --include="*.ts" -l
grep -r "dso" --include="*.tsx" --include="*.ts" -l
grep -r "neo-panel\|neo-inset\|lcd-screen\|lcd-graticule\|led-active\|tech-label\|breathing\|haptic-snap\|neo-press" --include="*.css" -l
grep -r "chassis\|bg-panel\b\|bg-lcd\|text-teal\|text-amber\|text-bright\|text-muted\|border-highlight" --include="*.tsx" --include="*.ts" -l
```

### 3. Build verification

```bash
cd frontend && npm run build
make frontend-lint
make frontend-format
```

All three must pass with zero errors.

### 4. Visual audit

Take screenshots of all pages and verify via MCP vision analysis:
- No dark backgrounds
- No teal/amber accent colors
- No LED indicators
- No scanlines
- No screw/vent decorations
- Warm cream background throughout
- White cards with subtle shadows
- Indigo accent color

---

## Acceptance Criteria

- [ ] Zero DSO CSS class names in any source file
- [ ] Zero DSO color token names in any source file
- [ ] Zero DSO component names in any source file
- [ ] `frontend/src/components/dso/` directory does not exist
- [ ] No visual artifacts resembling oscilloscope aesthetic
- [ ] `make frontend-lint` passes with zero errors
- [ ] `make frontend-format` passes with zero changes needed
- [ ] `npm run build` succeeds with zero errors
- [ ] MCP vision analysis confirms warm editorial design throughout

---

## Validation

1. Run grep audit — all searches return zero matches
2. `npm run build` — succeeds
3. `make frontend-lint` — zero errors
4. `make frontend-format` — zero changes
5. Screenshot all 10+ routes — MCP vision analysis confirms no DSO remnants
6. Final comprehensive visual review
