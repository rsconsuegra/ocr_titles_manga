# US-FRF3: Page Transition Animations

**Sub-phase**: FR-F — Polish
**Depends on**: US-FRB3 (layout with animate-fade-in class)
**Blocks**: US-FRF5 (final cleanup)

---

## Story

> As a user, I want subtle fade-in animations when navigating between pages so that transitions feel smooth rather than jarring.

---

## Scope

### In Scope
- Verify `animate-fade-in` class works on route changes
- Ensure animation is subtle (0.15s) and doesn't delay content

### Out of Scope
- Complex page transition animations (slide, morph)
- Animation on individual components

---

## Implementation Details

### 1. Verify existing implementation

In US-FRB3, the main content wrapper already has `animate-fade-in`:
```tsx
<div className="mx-auto max-w-6xl animate-fade-in">
  <Routes>...</Routes>
</div>
```

And in US-FRA3, the keyframe was defined:
```css
.animate-fade-in {
  animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
```

### 2. Force re-animation on route change

The issue: `animate-fade-in` on a static wrapper won't re-trigger on route change because the DOM element persists. Solution: add a `key` to the wrapper that changes on route change:

```tsx
import { useLocation } from "react-router-dom";

// In App.tsx layout:
const location = useLocation();

<div className="mx-auto max-w-6xl animate-fade-in" key={location.pathname}>
  <Routes location={location}>...</Routes>
</div>
```

The `key` prop forces React to remount the wrapper on route change, re-triggering the animation.

---

## Acceptance Criteria

- [ ] Main content area fades in on each route change
- [ ] Animation is 0.15s ease-out (subtle, not distracting)
- [ ] Animation does not delay content rendering (starts immediately)
- [ ] Animation works on all route changes
- [ ] Animation does not play on initial page load (optional, not blocking)

---

## Validation

1. Navigate between pages — verify subtle fade-in on each transition
2. Verify animation completes quickly (no visible delay)
3. Rapid navigation — verify no animation stacking or visual glitches
