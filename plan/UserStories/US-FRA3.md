# US-FRA3: Remove Neumorphic CSS

**Sub-phase**: FR-A — Design Foundation
**Depends on**: US-FRA1 (fonts), US-FRA2 (color tokens defined)
**Blocks**: US-FRB1 (layout needs clean CSS), US-FRC1–C7 (components need new utility classes)

---

## Story

> As a user, I want the app to stop using neumorphic/oscilloscope visual effects (raised panels, inset shadows, scanlines, LED indicators, LCD screens) so that the interface is clean and distraction-free.

---

## Scope

### In Scope
- Remove all DSO CSS classes from `index.css`
- Remove all DSO CSS keyframes
- Remove `:root` CSS variables for neumorphic shadows
- Remove custom scrollbar CSS
- Add new utility classes: `card-base`, `label-text`, `focus-ring`, `animate-fade-in`, `fade-pulse`
- Verify app still compiles

### Out of Scope
- Updating component code to stop referencing removed classes (FR-C7 handles cutover)
- Layout changes (FR-B)
- Page rewrites (FR-D, FR-E)

---

## Implementation Details

### 1. `frontend/src/index.css` (modified)

**Remove these CSS classes** (~80 lines total):

| Class | Purpose (DSO) |
|-------|---------------|
| `.neo-panel` | Raised panel with outward box-shadow |
| `.neo-inset` | Recessed area with inset shadow |
| `.neo-deep-inset` | Deeper recessed area |
| `.lcd-screen` | Dark screen with scanline sweep |
| `.lcd-screen::after` | Animated scanline overlay |
| `.lcd-screen > *` | Positioning for LCD children |
| `.lcd-graticule` | Dot-grid overlay |
| `.led` | LED indicator base |
| `.led-active` | Green active LED |
| `.led-amber` | Amber warning LED |
| `.led-off` | Inactive LED |
| `.tech-label` | Small caps technical label |
| `.tech-label-bright` | Bright variant of tech-label |
| `.breathing` | Breathing glow animation |
| `.haptic-snap` | Button click feedback animation |
| `.neo-press` | Button press effect |
| `.neo-press:active` | Active state for neo-press |

**Remove these keyframes**:

| Keyframe | Purpose |
|----------|---------|
| `@keyframes scanline-sweep` | Horizontal scanline |
| `@keyframes breathing-glow` | Opacity pulse |
| `@keyframes haptic-snap` | Button click steps |
| `@keyframes led-pulse` | LED activation pulse |

**Remove these `:root` variables**:

```css
/* REMOVE */
:root {
  --neo-shadow: ...;
  --neo-inset: ...;
  --neo-deep-inset: ...;
  --neo-shadow-sm: ...;
}
```

**Remove custom scrollbar CSS** (~8 lines):

```css
/* REMOVE */
::-webkit-scrollbar { ... }
::-webkit-scrollbar-track { ... }
::-webkit-scrollbar-thumb { ... }
.scrollbar-thin { ... }
```

### 2. Add new utility classes

```css
.card-base {
  @apply bg-snow rounded-lg shadow-sm border border-linen;
}

.label-text {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--color-sand);
}

.focus-ring {
  &:focus-visible {
    @apply outline-none ring-2 ring-indigo/20 ring-offset-2 border-indigo;
  }
}

.animate-fade-in {
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-pulse {
  animation: fadePulse 2s ease-in-out infinite;
}

@keyframes fadePulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

---

## Acceptance Criteria

- [ ] Zero DSO CSS classes remain in `index.css` (neo-panel, neo-inset, neo-deep-inset, lcd-screen, lcd-graticule, led, tech-label, breathing, haptic-snap, neo-press)
- [ ] Zero DSO keyframes remain (scanline-sweep, breathing-glow, haptic-snap, led-pulse)
- [ ] Zero `:root` neumorphic variables remain (--neo-shadow, --neo-inset, --neo-deep-inset, --neo-shadow-sm)
- [ ] Custom scrollbar CSS removed
- [ ] New utility classes added: `.card-base`, `.label-text`, `.focus-ring`, `.animate-fade-in`, `.fade-pulse`
- [ ] `fadeIn` keyframe defined (0.15s ease-out)
- [ ] `fadePulse` keyframe defined (2s ease-in-out infinite)
- [ ] `npm run build` succeeds
- [ ] App renders all pages (unstyled on cream background — pages will look broken until FR-B and FR-C are complete)

---

## Validation

1. `cd frontend && npm run build` — succeeds with zero errors
2. Grep `index.css` for `neo-`, `lcd-`, `led`, `scanline`, `breathing`, `haptic`, `tech-label` — zero matches
3. Open browser — pages render (ugly but functional) on cream background
