# US-FRB2: See Page Context in Top Bar

**Sub-phase**: FR-B — Layout Shell
**Depends on**: US-FRA1 (fonts), US-FRA2 (color tokens)
**Blocks**: US-FRB3 (full layout needs top bar)

---

## Story

> As a user, I want a thin top bar showing the current page title and contextual status so that I always know where I am in the application.

---

## Scope

### In Scope
- New `TopBar.tsx` component
- Page title derived from current route
- Connection status indicator (static)
- Optional `actions` prop for page-specific buttons

### Out of Scope
- Dynamic connection status checking (future enhancement)
- Wiring action buttons for specific pages (FR-D, FR-E)

---

## Implementation Details

### 1. `frontend/src/components/TopBar.tsx` (new)

```tsx
import { useLocation, matchPath } from "react-router-dom";
import type { ReactNode } from "react";

const PAGE_TITLES: { pattern: string; title: string }[] = [
  { pattern: "/runs/:id", title: "Run Detail" },
  { pattern: "/batches/:id", title: "Batch Detail" },
  { pattern: "/profiles/:id/edit", title: "Edit Profile" },
  { pattern: "/profiles/new", title: "New Profile" },
  { pattern: "/run/quick", title: "Quick Run" },
  { pattern: "/run/pipeline", title: "Upload Images" },
  { pattern: "/playground/ocr", title: "OCR Playground" },
  { pattern: "/playground/preprocess", title: "Preprocess Playground" },
  { pattern: "/runs", title: "Pipeline Runs" },
  { pattern: "/batches", title: "Batch Runs" },
  { pattern: "/catalog", title: "Catalog" },
  { pattern: "/profiles", title: "Profiles" },
  { pattern: "/settings", title: "Settings" },
  { pattern: "/", title: "Dashboard" },
];

function getPageTitle(pathname: string): string {
  for (const { pattern, title } of PAGE_TITLES) {
    if (matchPath(pattern, pathname)) {
      return title;
    }
  }
  return "Manga OCR";
}

interface TopBarProps {
  actions?: ReactNode;
}

export default function TopBar({ actions }: TopBarProps) {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <header className="h-14 bg-snow border-b border-linen flex items-center justify-between px-6 sticky top-0 z-10">
      <h2 className="font-display text-[20px] font-semibold text-ink">
        {pageTitle}
      </h2>
      <div className="flex items-center gap-4">
        {actions}
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-success" />
          <span className="text-[13px] text-charcoal font-body">Connected</span>
        </div>
      </div>
    </header>
  );
}
```

### Key Design Decisions

1. **Title matching order**: More specific patterns (with `:id`) listed first to avoid partial matches
2. **`matchPath`**: Uses React Router's built-in path matching for route patterns
3. **`actions` slot**: ReactNode prop for page-specific buttons (e.g., "Retry" on RunDetail, "Export CSV" on Catalog)
4. **Connection status**: Static green dot + "Connected" text for now; can be made dynamic later
5. **Sticky**: TopBar stays visible when scrolling within the main content area

---

## Acceptance Criteria

- [ ] TopBar renders h-14, bg-snow, border-b border-linen
- [ ] Left side shows page title in Playfair Display, 20px, weight-600, color-ink
- [ ] Page title is correct for all 14 routes
- [ ] Right side shows green dot + "Connected" text
- [ ] TopBar accepts optional `actions` ReactNode prop
- [ ] TopBar is sticky (stays visible on scroll)
- [ ] TopBar spans full width to the right of sidebar (when used in layout)

---

## Validation

1. Navigate to each route — verify correct title
2. `/runs/abc` → "Run Detail", `/profiles/abc/edit` → "Edit Profile"
3. Verify green dot visible on right side
