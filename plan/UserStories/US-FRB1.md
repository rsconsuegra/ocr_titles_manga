# US-FRB1: Navigate via Sidebar

**Sub-phase**: FR-B — Layout Shell
**Depends on**: US-FRA1 (fonts), US-FRA2 (color tokens), US-FRA3 (clean CSS)
**Blocks**: US-FRB3 (full layout needs sidebar), US-FRC7 (DSO removal needs sidebar in place)

---

## Story

> As a user, I want a persistent sidebar on the left side of the screen showing all navigation options so that I can quickly switch between sections without opening dropdown menus.

---

## Scope

### In Scope
- New `Sidebar.tsx` component with fixed left position
- Brand text, 4 nav sections, 11 nav items
- Active route detection via `useLocation()`
- Hover and active states

### Out of Scope
- TopBar (US-FRB2)
- App.tsx layout refactor (US-FRB3)
- Removing old navbar (US-FRB3)

---

## Implementation Details

### 1. `frontend/src/components/Sidebar.tsx` (new)

```tsx
import { NavLink, useLocation } from "react-router-dom";

const NAV_SECTIONS = [
  {
    label: "WORKFLOW",
    items: [
      { to: "/run/pipeline", text: "Upload Images" },
      { to: "/run/quick", text: "Quick Run" },
    ],
  },
  {
    label: "RESULTS",
    items: [
      { to: "/runs", text: "Pipeline Runs" },
      { to: "/batches", text: "Batch Runs" },
      { to: "/catalog", text: "Catalog" },
    ],
  },
  {
    label: "EXPERIMENT",
    items: [
      { to: "/playground/ocr", text: "OCR Playground" },
      { to: "/playground/preprocess", text: "Preprocess Playground" },
    ],
  },
  {
    label: "CONFIGURE",
    items: [
      { to: "/profiles", text: "Profiles" },
      { to: "/settings", text: "Settings" },
    ],
  },
];

const EXACT_ROUTES: Record<string, string> = {
  "/": "/",
  "/runs": "/runs",
  "/batches": "/batches",
  "/catalog": "/catalog",
  "/playground/ocr": "/playground/ocr",
  "/playground/preprocess": "/playground/preprocess",
  "/run/quick": "/run/quick",
  "/run/pipeline": "/run/pipeline",
  "/profiles": "/profiles",
  "/settings": "/settings",
};

const PREFIX_ROUTES: Record<string, string> = {
  "/runs/": "/runs",
  "/batches/": "/batches",
  "/profiles/": "/profiles",
};

export default function Sidebar() {
  const location = useLocation();

  const isActive = (to: string) => {
    if (location.pathname === to) return true;
    if (PREFIX_ROUTES[to + "/"] && location.pathname.startsWith(to + "/")) return true;
    if (to === "/run/pipeline" && location.pathname === "/upload") return true;
    if (to === "/playground/preprocess" && location.pathname === "/preprocess") return true;
    return false;
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-[220px] bg-sidebar border-r border-sidebar-border flex flex-col z-10">
      <div className="px-5 pt-6 pb-4">
        <h1 className="font-display text-[18px] font-semibold text-ink">
          Manga OCR
        </h1>
      </div>

      <nav className="flex-1 overflow-y-auto px-3">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-6">
            <div className="label-text px-3 mb-2">{section.label}</div>
            <ul>
              {section.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    className={() => {
                      const active = isActive(item.to);
                      return `block px-3 py-2 rounded-md text-[14px] font-body transition-colors ${
                        active
                          ? "bg-indigo-pale text-indigo font-semibold"
                          : "text-charcoal hover:bg-cream hover:text-ink"
                      }`;
                    }}
                  >
                    {item.text}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="px-5 py-4">
        <span className="text-[11px] text-sand font-body">v0.1</span>
      </div>
    </aside>
  );
}
```

### Key Design Decisions

1. **Active detection**: Uses `useLocation()` + prefix matching for detail/edit routes (e.g., `/runs/abc-123` highlights "Pipeline Runs")
2. **Alias routes**: `/upload` → highlights "Upload Images", `/preprocess` → highlights "Preprocess Playground"
3. **Fixed positioning**: Sidebar stays in place while main content scrolls
4. **Overflow**: `overflow-y-auto` in case many nav items are added later
5. **z-10**: Ensures sidebar is above main content

---

## Acceptance Criteria

- [ ] Sidebar renders at left edge, 220px wide, fixed position
- [ ] Background is `sidebar` (#FDFCFA) with `sidebar-border` right border
- [ ] "Manga OCR" brand text at top: Playfair Display, 18px, weight-600, color ink
- [ ] 4 nav sections with label-text style headers: WORKFLOW, RESULTS, EXPERIMENT, CONFIGURE
- [ ] 11 nav items total, each 14px font-body color-charcoal
- [ ] Active nav item: bg-indigo-pale, text-indigo, font-weight-600
- [ ] Hover state: bg-cream, text-ink
- [ ] `/runs/abc-123` highlights "Pipeline Runs" in sidebar
- [ ] `/profiles/abc/edit` highlights "Profiles" in sidebar
- [ ] `/upload` alias highlights "Upload Images"
- [ ] Sidebar does not scroll with page content
- [ ] "v0.1" text visible at bottom in sand color
- [ ] All nav links navigate to correct routes on click

---

## Validation

1. Screenshot the sidebar — verify 220px width, cream background, nav sections visible
2. Click each nav item — verify route changes and active highlight follows
3. Navigate to `/runs/some-id` — verify "Pipeline Runs" is highlighted
4. Scroll main content — verify sidebar stays fixed
