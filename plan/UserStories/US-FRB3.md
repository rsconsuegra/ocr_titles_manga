# US-FRB3: Full Layout Without Top Navbar

**Sub-phase**: FR-B — Layout Shell
**Depends on**: US-FRB1 (Sidebar), US-FRB2 (TopBar)
**Blocks**: US-FRC1–C7 (components render in new layout), all page stories

---

## Story

> As a user, I want the app layout to use sidebar + top bar instead of the current top navbar with dropdown menus so that navigation is always visible and accessible.

---

## Scope

### In Scope
- Rewrite `App.tsx` to use Sidebar + TopBar layout
- Remove DsoBrandStrip, DsoScrew, DsoVentGrille usage
- Remove NavGroup, SubLink, navLinkClass definitions
- Remove footer
- Set cream page background

### Out of Scope
- Creating new Sidebar/TopBar components (US-FRB1, US-FRB2)
- Updating page content (FR-D, FR-E)
- Removing DSO component imports from pages (FR-C7)

---

## Implementation Details

### 1. `frontend/src/App.tsx` (rewritten)

Replace the entire layout structure:

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import Dashboard from "./pages/Dashboard";
import Runs from "./pages/Runs";
import RunDetail from "./pages/RunDetail";
import BatchRuns from "./pages/BatchRuns";
import BatchRunDetail from "./pages/BatchRunDetail";
import Catalog from "./pages/Catalog";
import OcrPlayground from "./pages/OcrPlayground";
import PreprocessPlayground from "./pages/PreprocessPlayground";
import QuickRun from "./pages/QuickRun";
import Upload from "./pages/Upload";
import Profiles from "./pages/Profiles";
import ProfileEditor from "./pages/ProfileEditor";
import Settings from "./pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-cream">
        <Sidebar />
        <div className="flex-1 flex flex-col ml-[220px]">
          <TopBar />
          <main className="flex-1 p-6">
            <div className="mx-auto max-w-6xl animate-fade-in">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/runs" element={<Runs />} />
                <Route path="/runs/:id" element={<RunDetail />} />
                <Route path="/batches" element={<BatchRuns />} />
                <Route path="/batches/:id" element={<BatchRunDetail />} />
                <Route path="/catalog" element={<Catalog />} />
                <Route path="/playground/ocr" element={<OcrPlayground />} />
                <Route path="/playground/preprocess" element={<PreprocessPlayground />} />
                <Route path="/run/quick" element={<QuickRun />} />
                <Route path="/run/pipeline" element={<Upload />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/profiles" element={<Profiles />} />
                <Route path="/profiles/new" element={<ProfileEditor />} />
                <Route path="/profiles/:id/edit" element={<ProfileEditor />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/preprocess" element={<PreprocessPlayground />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}
```

### What gets removed from current App.tsx

1. **Imports**: `DsoBrandStrip`, `DsoScrew`, `DsoVentGrille` from `components/dso/`
2. **Functions**: `navLinkClass()`, `NavGroup` component, `SubLink` component
3. **Layout**: The `AppShell` component with header/footer using `DsoBrandStrip`
4. **Footer**: Entire footer element with version/status LED
5. **All DSO references**: Any `className` using DSO CSS classes

### Layout Structure

```
┌──────────────────────────────────────────────────┐
│ ┌─────────┐ ┌──────────────────────────────────┐ │
│ │         │ │ TopBar (h-14, bg-snow)           │ │
│ │         │ ├──────────────────────────────────┤ │
│ │ Sidebar │ │                                  │ │
│ │ (220px) │ │   Main Content                   │ │
│ │         │ │   (p-6, max-w-6xl, animate-fade) │ │
│ │         │ │                                  │ │
│ │         │ │                                  │ │
│ └─────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

---

## Acceptance Criteria

- [ ] `App.tsx` renders `<Sidebar>` on the left, `<TopBar>` + `<Routes>` on the right
- [ ] No `DsoBrandStrip`, `DsoScrew`, `DsoVentGrille` components used in App.tsx
- [ ] No `NavGroup`, `SubLink`, or `navLinkClass` functions in App.tsx
- [ ] Main content area has p-6 padding, max-w-6xl centered
- [ ] No footer element
- [ ] Page background is cream (#F7F4EF)
- [ ] Layout uses `flex min-h-screen` so content fills viewport height
- [ ] All 14 routes render correctly in the new layout
- [ ] `animate-fade-in` applied to content wrapper for page transitions
- [ ] `npm run build` succeeds

---

## Validation

1. `cd frontend && npm run build` — succeeds
2. Screenshot Dashboard — verify sidebar on left, top bar above content, cream background
3. Navigate through all routes — verify each page renders in main content area
4. Verify no dark navbar at top, no footer at bottom
