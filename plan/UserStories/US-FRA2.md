# US-FRA2: Apply Warm Editorial Color Palette

**Sub-phase**: FR-A — Design Foundation
**Depends on**: US-FRA1 (font tokens defined first)
**Blocks**: US-FRA3 (CSS cleanup needs new tokens), US-FRB1 (sidebar needs sidebar/sidebar-border tokens), all component and page stories

---

## Story

> As a user, I want the app to use warm cream backgrounds, clean white card surfaces, and an indigo accent color so that the interface feels inviting and editorial rather than cold and technical.

---

## Scope

### In Scope
- Replace all 14 DSO color tokens with 17 warm editorial tokens in `@theme`
- Verify new tokens are available via Tailwind utility classes

### Out of Scope
- Removing DSO CSS classes (US-FRA3)
- Updating components to use new tokens (FR-C)
- Updating pages (FR-D, FR-E)

---

## Implementation Details

### 1. `frontend/src/index.css` (modified — `@theme` block)

Replace the entire color section of `@theme`. Remove all 14 DSO tokens:

```css
/* REMOVE these DSO tokens */
--color-chassis: #1e2229;
--color-panel: #272d36;
--color-panel-light: #313842;
--color-inset: #2a3039;
--color-lcd: #141920;
--color-teal: #38b2ac;
--color-teal-dim: #2d8a84;
--color-teal-glow: #38b2ac66;
--color-amber: #d4a052;
--color-amber-dim: #b8884a;
--color-amber-glow: #d4a05266;
--color-bright: #e8ecf1;
--color-muted: #6b7a8d;
--color-surface-dark: #0a0c10;
--color-highlight: #373f4b;
```

Add 17 new tokens:

```css
@theme {
  --color-cream: #F7F4EF;
  --color-snow: #FFFFFF;
  --color-linen: #EDE8E0;
  --color-stone: #B8B0A6;
  --color-sand: #9B9288;
  --color-charcoal: #3A3632;
  --color-ink: #1A1714;
  --color-indigo: #2E4A7A;
  --color-indigo-light: #3D5F94;
  --color-indigo-pale: #E8EDF4;
  --color-vermillion: #C4603C;
  --color-vermillion-light: #D4785A;
  --color-success: #3D8B5F;
  --color-warning: #C4A23C;
  --color-error: #B84040;
  --color-sidebar: #FDFCFA;
  --color-sidebar-border: #E8E3DB;
}
```

### Color Token Reference

| Token | Hex | Usage |
|-------|-----|-------|
| `cream` | `#F7F4EF` | Page background |
| `snow` | `#FFFFFF` | Card surfaces, top bar |
| `linen` | `#EDE8E0` | Borders, dividers, table header bg |
| `stone` | `#B8B0A6` | Pending/cancelled badge bg, muted borders |
| `sand` | `#9B9288` | Section labels, secondary descriptions |
| `charcoal` | `#3A3632` | Body text, nav items |
| `ink` | `#1A1714` | Headings, page titles |
| `indigo` | `#2E4A7A` | Primary accent (buttons, links, active states) |
| `indigo-light` | `#3D5F94` | Button hover state |
| `indigo-pale` | `#E8EDF4` | Active filter bg, selected states |
| `vermillion` | `#C4603C` | Secondary accent, error/destructive actions |
| `vermillion-light` | `#D4785A` | Hover state for vermillion |
| `success` | `#3D8B5F` | Completed status, success feedback |
| `warning` | `#C4A23C` | Warning status, needs_review badge |
| `error` | `#B84040` | Failed status, error states, danger buttons |
| `sidebar` | `#FDFCFA` | Sidebar background |
| `sidebar-border` | `#E8E3DB` | Sidebar right border |

---

## Acceptance Criteria

- [ ] `@theme` defines exactly 17 color tokens
- [ ] No DSO color tokens remain in `@theme` (chassis, panel, lcd, teal, amber, bright, muted, highlight, panel-light, surface-dark, teal-dim, teal-glow, amber-dim, amber-glow)
- [ ] `bg-cream` applies `#F7F4EF`
- [ ] `bg-snow` applies `#FFFFFF`
- [ ] `text-indigo` applies `#2E4A7A`
- [ ] `text-ink` applies `#1A1714`
- [ ] `border-linen` applies `#EDE8E0`
- [ ] `bg-sidebar` applies `#FDFCFA`
- [ ] No TypeScript/build errors after token swap
- [ ] App still renders (pages may look broken due to missing old tokens — acceptable at this stage)

---

## Validation

1. `cd frontend && npm run build` — succeeds
2. Open browser, verify `bg-cream` renders as warm off-white
3. Inspect element → computed styles → verify `--color-cream` is `#F7F4EF`
