# US-FRA1: Load New Typography

**Sub-phase**: FR-A — Design Foundation
**Depends on**: None
**Blocks**: US-FRA2 (palette needs font tokens), US-FRB1 (sidebar needs font-body), all page stories

---

## Story

> As a user, I want the app to use elegant, warm typography (serif headings, clean sans-serif body text, Japanese-capable fonts) so that the interface feels refined and appropriate for a manga catalog tool.

---

## Scope

### In Scope
- Replace Google Fonts in `index.html`: remove Plus Jakarta Sans + DM Sans, add Playfair Display + Source Sans 3 + Noto Sans JP
- Define 3 font tokens in `@theme` block of `index.css`
- Verify fonts load and render correctly

### Out of Scope
- Color palette changes (US-FRA2)
- CSS class cleanup (US-FRA3)
- Component updates to use new fonts

---

## Implementation Details

### 1. `frontend/index.html` (modified)

Replace the Google Fonts `<link>` tags. Remove:
- Plus Jakarta Sans (300,400,500,600,700,800)
- DM Sans (400,500,700)

Add:
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link
  href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Playfair+Display:wght@400;600;700&family=Source+Sans+3:wght@400;500;600&display=swap"
  rel="stylesheet"
/>
```

### 2. `frontend/src/index.css` (modified — `@theme` block only)

Replace the font token definitions:

```css
@theme {
  --font-display: "Playfair Display", serif;
  --font-body: "Source Sans 3", sans-serif;
  --font-japanese: "Noto Sans JP", sans-serif;
}
```

Remove old font tokens:
```css
/* REMOVE these */
--font-display: "Plus Jakarta Sans", sans-serif;
--font-tech: "DM Sans", sans-serif;
```

---

## Acceptance Criteria

- [ ] `index.html` loads exactly 3 font families: Playfair Display, Source Sans 3, Noto Sans JP
- [ ] Old fonts (Plus Jakarta Sans, DM Sans) are no longer loaded
- [ ] `@theme` defines `--font-display`, `--font-body`, `--font-japanese`
- [ ] Old `--font-tech` token removed
- [ ] `font-display` class applies Playfair Display
- [ ] `font-body` class applies Source Sans 3
- [ ] Japanese text renders in Noto Sans JP when `font-japanese` is applied
- [ ] No console errors about missing fonts
- [ ] Fonts load within 2 seconds on broadband

---

## Validation

1. Open `http://localhost:5173` in browser
2. Open DevTools Network tab → filter by "fonts.googleapis.com" → verify 3 families loaded
3. Inspect any heading → computed `font-family` should include "Playfair Display"
4. No 404s on font requests
