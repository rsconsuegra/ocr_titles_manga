# Frontend Redesign Plan

**Phase**: Frontend Redesign (UI/UX Overhaul)  
**Scope**: Complete visual redesign of the React frontend — new design system, new layout, new component library, all 13 pages redesigned  
**Goal**: Transform the dark neumorphic "oscilloscope" UI into a warm editorial design with sidebar navigation that feels like a refined manga catalog tool  
**Prerequisite**: V2 (MVP Backend API) — complete frontend with DSO component library

---

## What We Are Building

A complete visual and structural redesign of the existing React frontend:

1. **New design system** — Warm editorial aesthetic with Japanese publishing influences: cream backgrounds, indigo accent, serif headings, generous whitespace
2. **New layout** — Sidebar navigation (left, 220px) + thin top context bar replacing the current top navbar with dropdown menus
3. **New component library** — `components/ui/` replacing `components/dso/`: Button, Card, Badge, Input, Select, Table, Pagination, ProgressBar, ErrorBanner, EmptyState, Sidebar, TopBar
4. **All 13 pages redesigned** — Same routes, same functionality, new visual treatment
5. **New typography** — Playfair Display (headings), Source Sans 3 (body), Noto Sans JP (Japanese text)

## What We Are NOT Building

- No new routes or pages (same 14 routes, same URLs)
- No new API endpoints or backend changes
- No new features or functionality (purely visual/structural redesign)
- No new dependencies (same React 19, react-router-dom 7, Tailwind CSS v4, js-yaml, react-image-crop)
- No dark mode toggle (warm light theme only)
- No mobile/responsive design (desktop only, unchanged)
- No state management library (keep useState/useEffect pattern)
- No authentication or authorization UI
- No internationalization framework
- No accessibility audit (keep existing a11y, don't regress)

---

## Design Tokens

### Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| `--color-cream` | `#F7F4EF` | Page background |
| `--color-snow` | `#FFFFFF` | Card/panel surfaces, sidebar background |
| `--color-linen` | `#EDE8E0` | Borders, dividers, subtle separators |
| `--color-stone` | `#D4CFC6` | Disabled states, muted borders |
| `--color-sand` | `#9B9488` | Secondary text, labels |
| `--color-charcoal` | `#3D3831` | Primary text |
| `--color-ink` | `#1A1714` | Headings, emphasis text |
| `--color-indigo` | `#2E4A7A` | Primary accent (links, active states, buttons) |
| `--color-indigo-light` | `#3D6098` | Hover/pressed accent states |
| `--color-indigo-pale` | `#E8EDF5` | Accent backgrounds, selection highlights |
| `--color-vermillion` | `#C4603C` | CTAs, important actions, danger |
| `--color-vermillion-light` | `#D47A5A` | CTA hover state |
| `--color-success` | `#4A8C6F` | Completed states, success badges |
| `--color-warning` | `#C4963C` | Processing/warning states |
| `--color-error` | `#B94A4A` | Failed states, error messages |
| `--color-sidebar` | `#FDFCFA` | Sidebar background (slightly warmer than snow) |
| `--color-sidebar-border` | `#E8E3DB` | Sidebar right border |

### Typography

| Token | Font | Weights | Source |
|-------|------|---------|--------|
| `--font-display` | Playfair Display | 400, 600, 700 | Google Fonts |
| `--font-body` | Source Sans 3 | 400, 500, 600 | Google Fonts |
| `--font-japanese` | Noto Sans JP | 400, 500, 700 | Google Fonts |
| `--font-mono` | ui-monospace, SFMono-Regular, Menlo | 400 | System stack |

### Spacing & Radius

- **Base unit**: 4px. Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80
- **Border radius**: sm=6px, md=8px, lg=12px, xl=16px, full=9999px

### Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `shadow-sm` | `0 1px 2px rgba(26,23,20,0.05)` | Cards at rest |
| `shadow-md` | `0 2px 8px rgba(26,23,20,0.08)` | Elevated cards, dropdowns |
| `shadow-lg` | `0 4px 16px rgba(26,23,20,0.12)` | Modals, popovers |

---

## Target Directory Structure

```
frontend/
  index.html                              # Updated: new Google Fonts (Playfair Display, Source Sans 3, Noto Sans JP)
  src/
    index.css                             # Rewritten: new @theme tokens, remove all DSO CSS, new utility classes
    App.tsx                               # Rewritten: sidebar + topbar layout, remove DsoBrandStrip/NavGroup/SubLink
    main.tsx                              # Unchanged
    constants.ts                          # Unchanged
    vite-env.d.ts                         # Unchanged

    components/
      dso/                                # DELETED entirely
        DsoBadge.tsx                      # DELETED
        DsoBrandStrip.tsx                 # DELETED
        DsoButton.tsx                     # DELETED
        DsoCard.tsx                       # DELETED
        DsoErrorBanner.tsx                # DELETED
        DsoInput.tsx                      # DELETED
        DsoPagination.tsx                 # DELETED
        DsoProgressBar.tsx                # DELETED
        DsoSelect.tsx                     # DELETED
        DsoTable.tsx                      # DELETED
        index.ts                          # DELETED

      ui/                                 # NEW component library
        index.ts                          # Barrel exports
        Button.tsx                        # 4 variants: primary, secondary, danger, ghost
        Card.tsx                          # White bg, shadow, optional header
        Badge.tsx                         # Pill-shaped status badges
        Input.tsx                         # Text input with label
        Select.tsx                        # Dropdown select with label
        Table.tsx                         # Generic typed table
        Pagination.tsx                    # Prev/next with counter
        ProgressBar.tsx                   # Thin rounded bar
        ErrorBanner.tsx                   # Error display with left border
        EmptyState.tsx                    # Centered icon + message
        Sidebar.tsx                       # Left nav with sections
        TopBar.tsx                        # Breadcrumb + actions + status

      ConfidenceMeter.tsx                 # Updated: new ProgressBar, same logic
      ImageCompare.tsx                    # Updated: warm styling
      ImageCropper.tsx                    # Updated: modal styling
      ImageUploader.tsx                   # Updated: warm dropzone styling
      LlmConfigSection.tsx               # Updated: new Input/Select/Card
      LlmExtractionCard.tsx              # Updated: new Card/Badge
      OcrModelCard.tsx                    # Updated: new Card/Button
      OcrResultCard.tsx                   # Updated: warm card styling
      OllamaModelSelector.tsx            # Updated: new Select
      PipelineFilmstrip.tsx              # Updated: warm styling
      PreprocessStepCard.tsx             # Updated: new Card/Input/Select
      PromptSettingsPanel.tsx            # Updated: new Input/Card
      RunStatusBadge.tsx                  # Updated: new Badge variants
      SingleImageUpload.tsx              # Updated: warm dropzone

    pages/
      Dashboard.tsx                       # Redesigned: warm welcome, quick actions, stats, recent runs
      Runs.tsx                            # Redesigned: clean table, status filter pills
      RunDetail.tsx                       # Redesigned: two-column image + results
      BatchRuns.tsx                       # Redesigned: card-based list
      BatchRunDetail.tsx                  # Redesigned: progress + runs table
      Catalog.tsx                         # Redesigned: searchable table, inline editing
      OcrPlayground.tsx                   # Redesigned: two-panel layout
      PreprocessPlayground.tsx            # Redesigned: step pipeline + before/after
      QuickRun.tsx                        # Redesigned: upload -> configure -> results flow
      Upload.tsx                          # Redesigned: large dropzone, profile selector
      Profiles.tsx                        # Redesigned: clean table with actions
      ProfileEditor.tsx                   # Redesigned: multi-section form
      Settings.tsx                        # Redesigned: two-section settings form

    api/                                  # Unchanged (all 9 files)
    hooks/                                # Unchanged (all 4 hooks)
    utils/                                # Unchanged
```

---

## Implementation Steps

### Step 1: Design System Foundation

**Task**: Replace all design tokens, load new fonts, remove DSO CSS. No layout or component logic changes.

**1a. Load new fonts in `index.html`**

Replace the current Google Fonts link (Plus Jakarta Sans + DM Sans) with:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Playfair+Display:wght@400;600;700&family=Source+Sans+3:wght@400;500;600&display=swap" rel="stylesheet" />
```

**1b. Replace `@theme` block in `index.css`**

Replace the entire `@theme { ... }` block with the new design tokens defined above:

```css
@theme {
  --color-cream: #F7F4EF;
  --color-snow: #FFFFFF;
  --color-linen: #EDE8E0;
  --color-stone: #D4CFC6;
  --color-sand: #9B9488;
  --color-charcoal: #3D3831;
  --color-ink: #1A1714;
  --color-indigo: #2E4A7A;
  --color-indigo-light: #3D6098;
  --color-indigo-pale: #E8EDF5;
  --color-vermillion: #C4603C;
  --color-vermillion-light: #D47A5A;
  --color-success: #4A8C6F;
  --color-warning: #C4963C;
  --color-error: #B94A4A;
  --color-sidebar: #FDFCFA;
  --color-sidebar-border: #E8E3DB;

  --font-display: "Playfair Display", serif;
  --font-body: "Source Sans 3", sans-serif;
  --font-japanese: "Noto Sans JP", sans-serif;
}
```

**1c. Remove all DSO custom CSS**

Delete from `index.css`:
- `:root` CSS variables block (`--neo-shadow`, `--neo-inset`, `--neo-deep-inset`, `--neo-shadow-sm`)
- Scrollbar styling (`* { scrollbar-width... }`, `::-webkit-scrollbar` rules)
- `@keyframes scanline-sweep`
- `@keyframes breathing-glow`
- `@keyframes haptic-snap`
- `@keyframes led-pulse`
- `.neo-panel`, `.neo-inset`, `.neo-deep-inset`
- `.lcd-screen` (and `::after`, `> *` rules)
- `.lcd-graticule`
- `.led`, `.led-active`, `.led-amber`, `.led-off`
- `.tech-label`, `.tech-label-bright`
- `.breathing`, `.haptic-snap`, `.neo-press`

**1d. Add new utility CSS classes**

```css
.card-base {
  background: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(26, 23, 20, 0.05);
  border: 1px solid #EDE8E0;
}

.card-base:hover {
  box-shadow: 0 2px 8px rgba(26, 23, 20, 0.08);
}

.label-text {
  font-family: "Source Sans 3", sans-serif;
  font-size: 12px;
  font-weight: 500;
  color: #9B9488;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.focus-ring {
  outline: none;
}

.focus-ring:focus-visible {
  outline: 2px solid #2E4A7A;
  outline-offset: 2px;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in {
  animation: fade-in 0.15s ease-out;
}
```

**Files modified**:
- `frontend/index.html`
- `frontend/src/index.css`

**Verification**: App compiles. Pages render with raw/unstyled appearance on cream background. No console errors from missing CSS classes. All routes still work.

---

### Step 2: Layout Shell — Sidebar + Top Context Bar

**Task**: Replace the top navbar and footer with a left sidebar navigation and thin top context bar.

**2a. Create `Sidebar` component**

New file: `frontend/src/components/ui/Sidebar.tsx`

**Behavior**:
- Fixed left sidebar, 220px wide
- Top: "Manga OCR" brand text in Playfair Display (font-display), 18px, font-weight 600, color ink
- Below brand: thin linen divider
- Navigation organized in 4 sections, each with a section label and nav items:

  ```
  WORKFLOW
    Dashboard       /           (icon: layout-dashboard)
    Upload          /run/pipeline (icon: upload)
    Quick Run       /run/quick   (icon: zap)

  RESULTS
    Runs            /runs        (icon: list)
    Batches         /batches     (icon: layers)
    Catalog         /catalog     (icon: book-open)

  EXPERIMENT
    OCR Playground  /playground/ocr (icon: scan)
    Preprocessing   /playground/preprocess (icon: image)

  CONFIGURE
    Profiles        /profiles    (icon: settings)
    Settings        /settings    (icon: cog)
  ```

- Section labels: 10px uppercase, letter-spacing 1px, color sand, font-body 500
- Nav items: Source Sans 3 14px, color charcoal, rounded-md, padding 8px 12px
- Active state: bg-indigo-pale, text-indigo, font-weight 600
- Hover state: bg-cream (slightly darker than sidebar), text-ink
- Bottom of sidebar: small version text "v0.1" in sand color
- Active route detection via `useLocation()` + `startsWith` matching
- Collapsible: not in initial implementation (always expanded)

**2b. Create `TopBar` component**

New file: `frontend/src/components/ui/TopBar.tsx`

**Behavior**:
- Thin horizontal bar (h-14) spanning the content area (right of sidebar)
- Background: snow, bottom border: linen
- Left: Page title in font-display, 20px, font-weight 600, color ink
- Right: Status indicator (small green dot + "Connected" or amber dot + "Disconnected")
- Page title derived from current route via a lookup map:

  ```
  /              -> "Dashboard"
  /runs          -> "Pipeline Runs"
  /runs/:id      -> "Run Detail"
  /batches       -> "Batch Runs"
  /batches/:id   -> "Batch Detail"
  /catalog       -> "Catalog"
  /playground/ocr -> "OCR Playground"
  /playground/preprocess -> "Preprocessing"
  /run/quick     -> "Quick Run"
  /run/pipeline  -> "Upload Images"
  /profiles      -> "Profiles"
  /profiles/new  -> "New Profile"
  /profiles/:id/edit -> "Edit Profile"
  /settings      -> "Settings"
  ```

- Accept `actions?: React.ReactNode` prop for page-specific action buttons (rendered right of title)

**2c. Refactor `App.tsx`**

Replace the entire layout structure:

- Remove imports: `DsoBrandStrip`, `DsoScrew`, and all DSO imports
- Remove: `navLinkClass`, `NavGroup`, `SubLink` functions
- New layout structure:

  ```tsx
  <div className="flex min-h-screen bg-cream">
    <Sidebar />
    <div className="flex flex-1 flex-col">
      <TopBar />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto w-full max-w-6xl">
          <Routes>
            {/* same routes */}
          </Routes>
        </div>
      </main>
    </div>
  </div>
  ```

- All `<Route>` elements remain unchanged (same paths, same components)

**Files created**:
- `frontend/src/components/ui/Sidebar.tsx`
- `frontend/src/components/ui/TopBar.tsx`

**Files modified**:
- `frontend/src/App.tsx`

**Verification**: All 14 routes render correctly in new layout. Sidebar highlights active route. TopBar shows correct page title. No DSO components used in layout.

---

### Step 3: Component Library — Button

**Task**: Create `Button` component replacing `DsoButton`.

New file: `frontend/src/components/ui/Button.tsx`

**Props**:

```typescript
interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
}
```

**Variants**:
- `primary`: bg-indigo text-snow, hover:bg-indigo-light, active:scale-[0.98]
- `secondary`: bg-snow text-charcoal border-linen, hover:bg-cream
- `danger`: bg-error text-snow, hover:bg-error/90
- `ghost`: bg-transparent text-charcoal, hover:bg-cream

**Sizes**:
- `sm`: px-3 py-1.5 text-sm
- `md`: px-4 py-2 text-sm (default)
- `lg`: px-6 py-3 text-base

**Shared**: rounded-lg, font-body font-medium, transition-all duration-150, disabled:opacity-40 cursor-not-allowed

**Files created**:
- `frontend/src/components/ui/Button.tsx`

---

### Step 4: Component Library — Card

**Task**: Create `Card` component replacing `DsoCard`.

New file: `frontend/src/components/ui/Card.tsx`

**Props**:

```typescript
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  accent?: "indigo" | "vermillion" | "success" | "warning" | "none";
  padding?: "sm" | "md" | "lg";
}
```

**Behavior**:
- Base: bg-snow rounded-lg shadow-sm border border-linen
- `accent`: top border of 3px in accent color (default none)
- `padding`: sm=p-3, md=p-5 (default), lg=p-6
- Optional `<Card.Header>` sub-component: font-display text-lg font-600 text-ink, with optional right-side action slot

**Files created**:
- `frontend/src/components/ui/Card.tsx`

---

### Step 5: Component Library — Badge

**Task**: Create `Badge` component replacing `DsoBadge`.

New file: `frontend/src/components/ui/Badge.tsx`

**Props**:

```typescript
interface BadgeProps {
  status: "pending" | "processing" | "completed" | "failed" | "cancelled" | "review" | "default";
  size?: "sm" | "md";
}
```

**Status colors** (pill-shaped, rounded-full):
- `pending`: bg-stone/20 text-sand
- `processing`: bg-indigo-pale text-indigo (with subtle pulse animation)
- `completed`: bg-success/15 text-success
- `failed`: bg-error/15 text-error
- `cancelled`: bg-stone/20 text-sand
- `review`: bg-warning/15 text-warning
- `default`: bg-linen text-sand

**Size**:
- `sm`: px-2 py-0.5 text-xs
- `md`: px-2.5 py-1 text-sm (default)

**Files created**:
- `frontend/src/components/ui/Badge.tsx`

---

### Step 6: Component Library — Input, Select

**Task**: Create `Input` and `Select` components replacing `DsoInput` and `DsoSelect`.

**Input** (`frontend/src/components/ui/Input.tsx`):

```typescript
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}
```

- Base: bg-snow border border-linen rounded-md px-3 py-2 text-charcoal font-body
- Focus: border-indigo ring-2 ring-indigo/20
- Error: border-error, helper text below in text-error
- Label: label-text class above input

**Select** (`frontend/src/components/ui/Select.tsx`):

```typescript
interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
  error?: string;
}
```

- Same styling as Input
- Custom chevron via background-image SVG
- appearance-none for consistent cross-browser look

**Files created**:
- `frontend/src/components/ui/Input.tsx`
- `frontend/src/components/ui/Select.tsx`

---

### Step 7: Component Library — Table, Pagination, ProgressBar, ErrorBanner, EmptyState

**Task**: Create remaining utility components.

**Table** (`frontend/src/components/ui/Table.tsx`):

```typescript
interface TableProps<T> {
  columns: { key: keyof T; header: string; render?: (row: T) => React.ReactNode; className?: string }[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}
```

- Header: bg-cream text-sand label-text style, px-4 py-3
- Rows: bg-snow border-b border-linen, hover:bg-cream/50
- Clickable rows: cursor-pointer

**Pagination** (`frontend/src/components/ui/Pagination.tsx`):

```typescript
interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
}
```

- Prev/Next buttons (ghost variant), "X-Y of Z" counter in sand text

**ProgressBar** (`frontend/src/components/ui/ProgressBar.tsx`):

```typescript
interface ProgressBarProps {
  value: number;
  max?: number;
  size?: "sm" | "md";
  showLabel?: boolean;
}
```

- Rounded-full track bg-linen
- Fill: success (>=70%), warning (>=30%), error (<30%)
- Size: sm=h-1.5, md=h-2.5
- Optional percentage label to the right

**ErrorBanner** (`frontend/src/components/ui/ErrorBanner.tsx`):

```typescript
interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
}
```

- bg-error/5 border-l-4 border-error text-error rounded-md p-4
- Dismiss X button top-right

**EmptyState** (`frontend/src/components/ui/EmptyState.tsx`):

```typescript
interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}
```

- Centered layout: icon (48px), title in font-display text-ink, description in sand
- Optional action button at bottom

**Files created**:
- `frontend/src/components/ui/Table.tsx`
- `frontend/src/components/ui/Pagination.tsx`
- `frontend/src/components/ui/ProgressBar.tsx`
- `frontend/src/components/ui/ErrorBanner.tsx`
- `frontend/src/components/ui/EmptyState.tsx`

---

### Step 8: Component Library — Barrel Export + DSO Cutover

**Task**: Create barrel export, delete DSO directory, update all imports.

**8a. Create barrel export**

New file: `frontend/src/components/ui/index.ts`

```typescript
export { Badge } from "./Badge";
export { Button } from "./Button";
export { Card } from "./Card";
export { EmptyState } from "./EmptyState";
export { ErrorBanner } from "./ErrorBanner";
export { Input } from "./Input";
export { Pagination } from "./Pagination";
export { ProgressBar } from "./ProgressBar";
export { Select } from "./Select";
export { Sidebar } from "./Sidebar";
export { Table } from "./Table";
export { TopBar } from "./TopBar";
```

**8b. Delete DSO directory**

Delete: `frontend/src/components/dso/` (11 files)

**8c. Update all imports across the codebase**

Global find-and-replace in all `.tsx` and `.ts` files:

| Old import | New import |
|-----------|-----------|
| `from "./components/dso"` or `from "../components/dso"` | `from "./components/ui"` or `from "../components/ui"` |
| `DsoButton` | `Button` |
| `DsoCard` | `Card` |
| `DsoBadge` | `Badge` |
| `DsoInput` | `Input` |
| `DsoSelect` | `Select` |
| `DsoTable`, `DsoTh`, `DsoTd` | `Table` (restructured API) |
| `DsoPagination` | `Pagination` |
| `DsoProgressBar` | `ProgressBar` |
| `DsoErrorBanner` | `ErrorBanner` |
| `DsoBrandStrip`, `DsoScrew`, `DsoVentGrille` | Removed (no replacement, handled by Sidebar/TopBar) |

**API adjustments per component**:

- `DsoButton variant="primary|secondary|amber|danger|ghost"` -> `Button variant="primary|secondary|danger|ghost"` (amber removed, use secondary or danger)
- `DsoCard variant="flat|inset|lcd"` -> `Card` (all same, use accent prop for differentiation)
- `DsoBadge variant="pending|processing|completed|failed|cancelled|default|review"` -> `Badge status="pending|processing|completed|failed|cancelled|default|review"`
- `DsoTable` -> `Table` with columns-based API (requires page-level refactoring)

**8d. Update shared components**

Each shared component file updated to use new UI imports:

| File | Changes |
|------|---------|
| `ConfidenceMeter.tsx` | Replace `DsoProgressBar` with `ProgressBar` |
| `OcrResultCard.tsx` | Replace `DsoCard`/`DsoBadge` with `Card`/`Badge` |
| `OcrModelCard.tsx` | Replace `DsoCard`/`DsoButton` with `Card`/`Button` |
| `RunStatusBadge.tsx` | Map status -> new `Badge` status |
| `SingleImageUpload.tsx` | Replace `DsoButton` with `Button` |
| `ImageUploader.tsx` | Replace `DsoButton`/`DsoCard` with `Button`/`Card` |
| `LlmConfigSection.tsx` | Replace `DsoCard`/`DsoSelect`/`DsoInput` with `Card`/`Select`/`Input` |
| `LlmExtractionCard.tsx` | Replace `DsoCard`/`DsoBadge`/`DsoProgressBar` with `Card`/`Badge`/`ProgressBar` |
| `PromptSettingsPanel.tsx` | Replace `DsoCard`/`DsoInput` with `Card`/`Input` |
| `OllamaModelSelector.tsx` | Replace `DsoSelect` with `Select` |
| `PreprocessStepCard.tsx` | Replace `DsoCard`/`DsoInput`/`DsoSelect`/`DsoButton` with new equivalents |
| `PipelineFilmstrip.tsx` | Replace `DsoCard` with `Card` |

**Files modified**:
- All 13 page files in `src/pages/`
- All 14 shared component files in `src/components/`
- `src/App.tsx` (if not already updated in Step 2)

**Files deleted**:
- `frontend/src/components/dso/` (entire directory: 11 files)

**Files created**:
- `frontend/src/components/ui/index.ts`

**Verification**: `npm run build` succeeds with zero TypeScript errors. All pages render without runtime errors. No DSO references remain in codebase.

---

### Step 9: Dashboard Redesign

**Task**: Redesign the Dashboard page as a warm, inviting entry point.

New file content: `frontend/src/pages/Dashboard.tsx` (full rewrite)

**Layout**:

```
+----------------------------------------------+
| Welcome to Manga OCR                         |
| Extract and catalog manga titles with OCR     |
+--------------+--------------+----------------+
| Upload       | Quick Run    | OCR Playground  |
| Images       |              |                 |
| description  | description  | description     |
| [-> Go]      | [-> Go]      | [-> Go]         |
+--------------+--------------+----------------+
| Recent Runs                                   |
| +------------------------------------------+ |
| | run table (5 rows) with status badges    | |
| +------------------------------------------+ |
+----------+----------+----------+-------------+
| Total    | Completed| Failed   | Avg Conf     |
| 42       | 38       | 2        | 87%          |
+----------+----------+----------+-------------+
```

**Components used**: Card (with accent), Badge, Button, Table

**Data sources** (existing API):
- `getDashboardStats()` for stats
- `listRuns({ limit: 5 })` for recent runs

**Files modified**:
- `frontend/src/pages/Dashboard.tsx`

**Verification**: Screenshot -> warm editorial appearance, no DSO remnants, all data loads correctly.

---

### Step 10: Core Workflow Pages

**Task**: Redesign the 5 most-used pages in the OCR workflow.

**10a. Upload page** (`frontend/src/pages/Upload.tsx`)

Layout:
- Two-column on large screens: left (60%) = dropzone + image grid, right (40%) = profile selector + config
- Dropzone: large dashed-border area (border-linen, rounded-xl), cream bg, indigo accent on hover/drag
- Image grid: 3-column thumbnails with remove button
- Profile selector: Select component
- Submit button: Button primary "Start Processing"
- Below: list of created runs with status badges

**10b. Quick Run page** (`frontend/src/pages/QuickRun.tsx`)

Layout:
- Two-column: left = image upload + preview, right = configuration panels
- Configuration: collapsible sections (Card components) for Preprocessing, OCR, LLM
- Below both columns: results section (OcrResultCard + LlmExtractionCard)
- "Run" button: Button primary

**10c. Runs page** (`frontend/src/pages/Runs.tsx`)

Layout:
- Top: status filter as pill buttons (All / Pending / Processing / Completed / Failed)
- Table: columns = Image (thumbnail), Status (Badge), Created, Completed, Actions
- Clickable rows navigate to `/runs/:id`
- Pagination at bottom

**10d. Run Detail page** (`frontend/src/pages/RunDetail.tsx`)

Layout:
- Two-column: left (40%) = large image preview, right (60%) = results
- Right column sections:
  - Run metadata (status badge, timestamps)
  - OCR Results (collapsible cards per model)
  - Post-Processing Result (LlmExtractionCard)
  - Override form (inputs + save button)
- TopBar actions: Retry, Cancel buttons (contextual based on status)

**10e. Update shared components for new design**

| Component | Changes |
|-----------|---------|
| `OcrResultCard.tsx` | Card-based layout, Badge for model name, warm text styling |
| `RunStatusBadge.tsx` | Map status strings to new Badge status prop |
| `SingleImageUpload.tsx` | Warm dropzone, Button for actions |
| `ImageUploader.tsx` | Grid of thumbnails with warm borders, Button primary for upload |
| `ConfidenceMeter.tsx` | Wraps new ProgressBar with percentage label |

**Files modified**:
- `frontend/src/pages/Upload.tsx`
- `frontend/src/pages/QuickRun.tsx`
- `frontend/src/pages/Runs.tsx`
- `frontend/src/pages/RunDetail.tsx`
- `frontend/src/components/OcrResultCard.tsx`
- `frontend/src/components/RunStatusBadge.tsx`
- `frontend/src/components/SingleImageUpload.tsx`
- `frontend/src/components/ImageUploader.tsx`
- `frontend/src/components/ConfidenceMeter.tsx`

**Verification**: Screenshot each page. All API calls work. Status polling still functions. Image upload works.

---

### Step 11: Batch & Catalog Pages

**Task**: Redesign batch management and catalog pages.

**11a. BatchRuns page** (`frontend/src/pages/BatchRuns.tsx`)

Layout:
- Card-based list (not table): each batch = Card with:
  - Batch name (font-display), status Badge, progress bar
  - "X/Y completed" text, created date
  - "View Details" Button ghost
- Pagination at bottom
- "Create Batch" Button primary in TopBar actions

**11b. BatchRunDetail page** (`frontend/src/pages/BatchRunDetail.tsx`)

Layout:
- Top: progress overview card (ProgressBar + stats: completed/failed/pending counts)
- Below: Table of runs in batch with status badges
- TopBar actions: "Retry Failed" Button (if any failed)

**11c. Catalog page** (`frontend/src/pages/Catalog.tsx`)

Layout:
- Search bar (Input) + status filter pills (All / Confirmed / Needs Review / Rejected)
- Table: title_en, title_ja, code, confidence (ProgressBar), status (Badge), date
- Click row to expand: inline edit form with Input fields + save Button
- TopBar actions: "Export CSV" Button secondary

**Files modified**:
- `frontend/src/pages/BatchRuns.tsx`
- `frontend/src/pages/BatchRunDetail.tsx`
- `frontend/src/pages/Catalog.tsx`

**Verification**: Screenshot each page. Search, filter, pagination, inline editing all work.

---

### Step 12: Playground & Configuration Pages

**Task**: Redesign experiment and configuration pages.

**12a. OCR Playground** (`frontend/src/pages/OcrPlayground.tsx`)

Layout:
- Two-panel: left = upload + model selection + LLM config, right = results
- Model selection: radio-style cards (Card with selected border accent)
- LLM config: LlmConfigSection component in collapsible Card
- Results: OcrResultCard + LlmExtractionCard

**12b. Preprocess Playground** (`frontend/src/pages/PreprocessPlayground.tsx`)

Layout:
- Left: image upload + step pipeline bar (horizontal step indicators)
- Right: ImageCompare (before/after) for selected step
- Step config: PreprocessStepCard below pipeline bar
- Export config: Button secondary

**12c. Update playground shared components**

| Component | Changes |
|-----------|---------|
| `ImageCompare.tsx` | Side-by-side with "Before"/"After" labels, warm borders |
| `PreprocessStepCard.tsx` | Card-based, new Input/Select for params |
| `LlmConfigSection.tsx` | Card-based, new Select/Input/Radio |
| `LlmExtractionCard.tsx` | Card with Badge, warm styling |
| `PromptSettingsPanel.tsx` | Collapsible Card with Textarea inputs |
| `OllamaModelSelector.tsx` | New Select component |
| `OcrModelCard.tsx` | Card with toggle switch, param inputs |
| `PipelineFilmstrip.tsx` | Horizontal scroll with warm Card thumbnails |

**12d. Profiles page** (`frontend/src/pages/Profiles.tsx`)

Layout:
- Table: name, description, default (Badge), created date, actions (edit/delete/export)
- TopBar actions: "New Profile" Button primary, "Import" Button secondary
- Import modal: fixed overlay with warm bg, Card container, file input + validate/import buttons

**12e. Profile Editor** (`frontend/src/pages/ProfileEditor.tsx`)

Layout:
- Multi-section form in stacked Cards:
  - Section 1: Name + description (Input)
  - Section 2: Preprocessing config (PreprocessStepCard instances)
  - Section 3: OCR config (OcrModelCard instances)
  - Section 4: LLM config (LlmConfigSection + PromptSettingsPanel)
- TopBar actions: "Save" Button primary, "Cancel" Button ghost
- For edit mode: load existing profile data on mount

**12f. Settings page** (`frontend/src/pages/Settings.tsx`)

Layout:
- Two sections in Cards:
  - Ollama Connection: URL input, ping button, status indicator, model selectors
  - API Credentials: OpenRouter key input (masked), validate/save/delete buttons
- Clean form layout with Input/Button components

**Files modified**:
- `frontend/src/pages/OcrPlayground.tsx`
- `frontend/src/pages/PreprocessPlayground.tsx`
- `frontend/src/pages/Profiles.tsx`
- `frontend/src/pages/ProfileEditor.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/ImageCompare.tsx`
- `frontend/src/components/PreprocessStepCard.tsx`
- `frontend/src/components/LlmConfigSection.tsx`
- `frontend/src/components/LlmExtractionCard.tsx`
- `frontend/src/components/PromptSettingsPanel.tsx`
- `frontend/src/components/OllamaModelSelector.tsx`
- `frontend/src/components/OcrModelCard.tsx`
- `frontend/src/components/PipelineFilmstrip.tsx`

**Verification**: Screenshot each page. All interactive features work (model selection, LLM config, profile CRUD, settings save).

---

### Step 13: Polish & Micro-interactions

**Task**: Final visual polish across all pages.

**13a. Loading states**

Replace all "breathing" animation references with a subtle fade-pulse. Use Tailwind's built-in `animate-pulse` for loading skeletons.

**13b. Empty states**

Add `EmptyState` component to all list pages when data arrays are empty:
- Runs: "No pipeline runs yet" + "Upload images to get started" + Upload button
- Batches: "No batch runs" + "Create Batch" button
- Catalog: "No catalog entries" + description
- Profiles: "No profiles" + "Create Profile" button

**13c. Page transitions**

Add `animate-fade-in` class to the `<main>` content wrapper for subtle fade-in on route changes.

**13d. Hover/focus states**

Verify all interactive elements have:
- Hover: visible bg change (cream or indigo-pale)
- Focus: `focus-ring` style (2px indigo outline, 2px offset)
- Active: subtle scale (scale-[0.98]) for buttons

**13e. Form validation feedback**

- Error state: red border + red helper text below input
- Success state: green checkmark (optional)

**13f. Final visual QA**

Screenshot every page, verify:
- Consistent spacing (p-6 for main, p-5 for cards)
- Consistent typography (font-display for headings, font-body for everything else)
- No DSO color references (teal, amber, panel, chassis, etc.)
- No broken layouts at 1280px+ width
- Image thumbnails load and display correctly
- Status badges use correct colors

**Files modified**:
- `frontend/src/index.css` (add pulse animation if needed)
- `frontend/src/App.tsx` (add fade-in animation to main)
- All page files (add EmptyState where needed)

**Verification**: `make frontend-lint` passes. `make frontend-format` passes. Visual QA screenshots approved.

---

## Component API Reference

### Button

```tsx
<Button variant="primary" size="md" onClick={handleClick}>
  Upload
</Button>
<Button variant="danger" disabled>
  Delete
</Button>
```

### Card

```tsx
<Card accent="indigo">
  <Card.Header title="OCR Results" action={<Button size="sm">Export</Button>} />
  <p>Content here</p>
</Card>
```

### Badge

```tsx
<Badge status="completed" />
<Badge status="processing" size="sm" />
```

### Input

```tsx
<Input label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
<Input label="URL" error="Invalid URL format" />
```

### Select

```tsx
<Select
  label="Model"
  options={[
    { value: "tesseract", label: "Tesseract" },
    { value: "paddle", label: "PaddleOCR" },
  ]}
  value={model}
  onChange={(e) => setModel(e.target.value)}
/>
```

### Table

```tsx
<Table
  columns={[
    { key: "status", header: "Status", render: (row) => <Badge status={row.status} /> },
    { key: "created_at", header: "Created" },
  ]}
  data={runs}
  onRowClick={(row) => navigate(`/runs/${row.id}`)}
  emptyMessage="No runs yet"
/>
```

### Pagination

```tsx
<Pagination total={100} limit={20} offset={0} onPageChange={setOffset} />
```

### ProgressBar

```tsx
<ProgressBar value={0.87} showLabel />
```

### EmptyState

```tsx
<EmptyState
  title="No runs yet"
  description="Upload manga images to start processing"
  action={<Button variant="primary">Upload Images</Button>}
/>
```

---

## Route Summary

Unchanged from current app:

| Route | Page | Step |
|-------|------|------|
| `/` | Dashboard | 9 |
| `/runs` | Runs | 10c |
| `/runs/:id` | RunDetail | 10d |
| `/batches` | BatchRuns | 11a |
| `/batches/:id` | BatchRunDetail | 11b |
| `/catalog` | Catalog | 11c |
| `/playground/ocr` | OcrPlayground | 12a |
| `/playground/preprocess` | PreprocessPlayground | 12b |
| `/run/quick` | QuickRun | 10b |
| `/run/pipeline` | Upload | 10a |
| `/profiles` | Profiles | 12d |
| `/profiles/new` | ProfileEditor | 12e |
| `/profiles/:id/edit` | ProfileEditor | 12e |
| `/settings` | Settings | 12f |

---

## Acceptance Criteria

- [ ] `npm run build` succeeds with zero TypeScript errors
- [ ] `make frontend-lint` passes with zero errors
- [ ] `make frontend-format` passes (no formatting changes needed)
- [ ] No file imports from `components/dso/` — entire directory deleted
- [ ] No DSO CSS classes in use (`neo-panel`, `neo-inset`, `lcd-screen`, `led`, `tech-label`, etc.)
- [ ] No DSO color tokens in use (`chassis`, `panel`, `lcd`, `teal`, `amber`, `bright`, `muted`)
- [ ] Sidebar renders on all pages, highlights active route
- [ ] TopBar shows correct page title for all 14 routes
- [ ] All 13 pages load without console errors
- [ ] All API integrations work (upload, runs, batches, catalog, profiles, settings)
- [ ] Image upload and preview work on Upload and QuickRun pages
- [ ] Status polling still functions for active runs/batches
- [ ] OCR playground runs OCR and displays results
- [ ] Preprocessing playground shows before/after comparison
- [ ] Profile CRUD (create, edit, delete, import, export) works
- [ ] Catalog search, filter, inline editing, CSV export work
- [ ] Settings page saves Ollama URL and API credentials
- [ ] Visual QA: all pages follow warm editorial aesthetic with cream bg, indigo accent, serif headings
- [ ] No "oscilloscope", "DSO", "LED", "LCD", "chassis", "panel" visual remnants
- [ ] Desktop viewport (1280px+) looks correct on all pages

---

## Implementation Order Summary

| Step | Description | New Files | Modified Files | Deleted Files |
|------|-------------|-----------|----------------|---------------|
| 1 | Design tokens + fonts | 0 | 2 | 0 |
| 2 | Layout (Sidebar + TopBar) | 2 | 1 | 0 |
| 3 | Button | 1 | 0 | 0 |
| 4 | Card | 1 | 0 | 0 |
| 5 | Badge | 1 | 0 | 0 |
| 6 | Input + Select | 2 | 0 | 0 |
| 7 | Table, Pagination, ProgressBar, ErrorBanner, EmptyState | 5 | 0 | 0 |
| 8 | Barrel export + DSO cutover | 1 | ~25 | 11 |
| 9 | Dashboard | 0 | 1 | 0 |
| 10 | Upload, QuickRun, Runs, RunDetail + shared components | 0 | 9 | 0 |
| 11 | BatchRuns, BatchRunDetail, Catalog | 0 | 3 | 0 |
| 12 | Playgrounds, Profiles, ProfileEditor, Settings + shared components | 0 | 13 | 0 |
| 13 | Polish + QA | 0 | ~5 | 0 |

**Totals**: ~12 new files, ~39 modified files, 11 deleted files
