# Frontend Redesign User Stories

These user stories cover the Frontend Redesign phase. They are organized by sub-phase: Design Foundation (FR-A), Layout Shell (FR-B), Component Library (FR-C), Core Pages (FR-D), Secondary Pages (FR-E), and Polish (FR-F).

---

## US-FRA1: Load New Typography

> As a user, I want the app to use elegant, warm typography (serif headings, clean sans-serif body text, Japanese-capable fonts) so that the interface feels refined and appropriate for a manga catalog tool.

**Acceptance Criteria**:
- `index.html` loads Playfair Display (400, 600, 700), Source Sans 3 (400, 500, 600), and Noto Sans JP (400, 500, 700) from Google Fonts
- Old fonts (Plus Jakarta Sans, DM Sans) are no longer loaded
- `@theme` block in `index.css` defines `--font-display: "Playfair Display", serif`, `--font-body: "Source Sans 3", sans-serif`, `--font-japanese: "Noto Sans JP", sans-serif`
- Headings throughout the app use font-display (Playfair Display)
- Body text and labels use font-body (Source Sans 3)
- Japanese text in catalog entries and OCR results renders in Noto Sans JP

---

## US-FRA2: Apply Warm Editorial Color Palette

> As a user, I want the app to use warm cream backgrounds, clean white card surfaces, and an indigo accent color so that the interface feels inviting and editorial rather than cold and technical.

**Acceptance Criteria**:
- `@theme` block in `index.css` defines all 17 new color tokens (cream, snow, linen, stone, sand, charcoal, ink, indigo, indigo-light, indigo-pale, vermillion, vermillion-light, success, warning, error, sidebar, sidebar-border)
- Page background is cream (#F7F4EF)
- Card surfaces are snow (#FFFFFF) with linen (#EDE8E0) borders
- Primary interactive accent is indigo (#2E4A7A)
- No DSO color tokens remain in `@theme` or any CSS (chassis, panel, lcd, teal, amber, bright, muted, highlight, panel-light, surface-dark, teal-dim, teal-glow, amber-dim, amber-glow)

---

## US-FRA3: Remove Neumorphic CSS

> As a user, I want the app to stop using neumorphic/oscilloscope visual effects (raised panels, inset shadows, scanlines, LED indicators, LCD screens) so that the interface is clean and distraction-free.

**Acceptance Criteria**:
- All DSO CSS classes removed from `index.css`: neo-panel, neo-inset, neo-deep-inset, lcd-screen (+ ::after, > * rules), lcd-graticule, led, led-active, led-amber, led-off, tech-label, tech-label-bright, breathing, haptic-snap, neo-press
- All DSO CSS keyframes removed: scanline-sweep, breathing-glow, haptic-snap, led-pulse
- All `:root` CSS variables removed: --neo-shadow, --neo-inset, --neo-deep-inset, --neo-shadow-sm
- Custom scrollbar CSS removed (scrollbar-width, ::-webkit-scrollbar rules)
- New utility classes added: card-base, label-text, focus-ring, animate-fade-in
- App still compiles and renders all pages (unstyled, on cream background)

---

## US-FRB1: Navigate via Sidebar

> As a user, I want a persistent sidebar on the left side of the screen showing all navigation options so that I can quickly switch between sections without opening dropdown menus.

**Acceptance Criteria**:
- Left sidebar is 220px wide, fixed position, background sidebar (#FDFCFA)
- Right border of sidebar is sidebar-border (#E8E3DB)
- Brand text "Manga OCR" at top in Playfair Display, 18px, font-weight 600, color ink
- Navigation organized in 4 labeled sections: WORKFLOW, RESULTS, EXPERIMENT, CONFIGURE
- Section labels: 10px uppercase, 1px letter-spacing, color sand
- 11 nav items total, each with label text in Source Sans 3, 14px, color charcoal
- Active nav item has bg-indigo-pale, text-indigo, font-weight 600
- Hovering a nav item shows bg-cream, text-ink
- Active route is detected via `useLocation()` and highlighted correctly for all 14 routes
- Sidebar does not scroll with page content (fixed viewport position)
- Bottom of sidebar shows "v0.1" version text in sand color

---

## US-FRB2: See Page Context in Top Bar

> As a user, I want a thin top bar showing the current page title and contextual status so that I always know where I am in the application.

**Acceptance Criteria**:
- Top bar is h-14, background snow, bottom border linen
- Top bar spans the full width to the right of the sidebar
- Left side shows page title in Playfair Display, 20px, font-weight 600, color ink
- Page title is correct for all 14 routes (e.g., "Dashboard", "Pipeline Runs", "Run Detail", etc.)
- Right side shows a connection status indicator: small green dot + "Connected" or amber dot + "Disconnected"
- TopBar accepts an optional `actions` prop for page-specific buttons

---

## US-FRB3: Full Layout Without Top Navbar

> As a user, I want the app layout to use sidebar + top bar instead of the current top navbar with dropdown menus so that navigation is always visible and accessible.

**Acceptance Criteria**:
- `App.tsx` renders Sidebar on the left, TopBar + main content on the right
- No DsoBrandStrip, DsoScrew, DsoVentGrille components used
- No NavGroup, SubLink, or navLinkClass functions in App.tsx
- Main content area has p-6 padding, max-w-6xl centered content
- All 14 routes render correctly in the new layout
- No footer element (removed)
- App background is cream (#F7F4EF)
- Layout uses `flex min-h-screen` so content fills viewport height

---

## US-FRC1: Use New Button Component

> As a user, I want buttons to have a clean, warm appearance with clear visual hierarchy (primary, secondary, danger, ghost) so that I can quickly identify the most important action on any page.

**Acceptance Criteria**:
- `Button` component supports 4 variants: primary (indigo bg, snow text), secondary (snow bg, charcoal text, linen border), danger (error bg, snow text), ghost (transparent bg, charcoal text)
- `Button` component supports 3 sizes: sm, md (default), lg
- All buttons have rounded-lg corners, font-body medium weight
- Primary buttons have hover:bg-indigo-light, active:scale-[0.98]
- Secondary buttons have hover:bg-cream
- Ghost buttons have hover:bg-cream
- Disabled buttons show opacity-40 and cursor-not-allowed
- Button extends native HTML button attributes (onClick, disabled, type, etc.)

---

## US-FRC2: Use New Card Component

> As a user, I want content to be organized in clean white cards with subtle shadows so that information is well-grouped and easy to scan.

**Acceptance Criteria**:
- `Card` component renders bg-snow, rounded-lg, shadow-sm, border border-linen
- Optional `accent` prop adds 3px top border in accent color (indigo, vermillion, success, warning)
- Optional `padding` prop: sm=p-3, md=p-5 (default), lg=p-6
- Optional `Card.Header` sub-component with title in font-display and optional action slot on the right
- Card hover effect: shadow-md (subtle elevation)

---

## US-FRC3: Use New Badge Component

> As a user, I want pipeline run and batch statuses displayed as small colored pills so that I can quickly assess the state of items in lists and tables.

**Acceptance Criteria**:
- `Badge` component supports 7 statuses: pending, processing, completed, failed, cancelled, review, default
- Each status has distinct background and text color (pending=stone, processing=indigo, completed=success, failed=error, cancelled=stone, review=warning, default=linen)
- Badges are pill-shaped (rounded-full)
- Processing badge has a subtle pulse animation
- Two sizes: sm (px-2 py-0.5 text-xs), md (px-2.5 py-1 text-sm, default)

---

## US-FRC4: Use New Input and Select Components

> As a user, I want form inputs and dropdowns to have consistent warm styling with clear focus states so that filling in forms feels polished and predictable.

**Acceptance Criteria**:
- `Input` component: bg-snow, border-linen, rounded-md, px-3 py-2, text-charcoal, font-body
- `Input` shows indigo focus ring (border-indigo, ring-2 ring-indigo/20) on focus
- `Input` shows error state: border-error with red helper text below
- `Input` accepts optional `label` prop rendered above in label-text style
- `Select` component has same base styling as Input
- `Select` uses appearance-none with custom chevron SVG
- `Select` accepts `options` array of `{ value, label }` objects
- Both components extend native HTML element attributes

---

## US-FRC5: Use New Table Component

> As a user, I want data displayed in clean tables with clear headers, hoverable rows, and consistent styling so that I can quickly scan and compare information.

**Acceptance Criteria**:
- `Table` component is generic typed `<T>` with column definitions
- Column definition includes: key, header text, optional render function, optional className
- Header row: bg-cream, label-text style, px-4 py-3
- Data rows: bg-snow, border-b border-linen, hover:bg-cream/50
- Clickable rows (via onRowClick): cursor-pointer
- Empty state: shows emptyMessage text centered when data array is empty

---

## US-FRC6: Use New Pagination, ProgressBar, ErrorBanner, EmptyState Components

> As a user, I want consistent pagination controls, progress indicators, error displays, and empty states across all pages so that the interface feels unified and predictable.

**Acceptance Criteria**:
- `Pagination`: prev/next buttons (ghost variant), "X-Y of Z" counter in sand text, disabled state when at boundaries
- `ProgressBar`: rounded-full track bg-linen, fill color based on value (success >=70%, warning >=30%, error <30%), two sizes (sm h-1.5, md h-2.5), optional percentage label
- `ErrorBanner`: bg-error/5, left border-4 border-error, text-error, rounded-md, optional dismiss X button
- `EmptyState`: centered layout with optional icon, title in font-display, description in sand, optional action button

---

## US-FRC7: Complete DSO Component Removal

> As a user, I want all neumorphic/oscilloscope components removed from the codebase so that the app has a single, consistent visual language.

**Acceptance Criteria**:
- `frontend/src/components/dso/` directory deleted entirely (11 files)
- No file imports from `components/dso/` anywhere in the codebase
- All 13 page files and 14 shared component files use `components/ui/` imports
- All `DsoButton` references replaced with `Button` (adjusted variant names)
- All `DsoCard` references replaced with `Card` (adjusted variant usage)
- All `DsoBadge` references replaced with `Badge` (variant -> status)
- All `DsoInput`/`DsoSelect` replaced with `Input`/`Select`
- All `DsoTable`/`DsoTh`/`DsoTd` replaced with `Table` (new columns API)
- All `DsoPagination`, `DsoProgressBar`, `DsoErrorBanner` replaced with new equivalents
- `DsoBrandStrip`, `DsoScrew`, `DsoVentGrille` removed entirely (replaced by Sidebar/TopBar)
- `npm run build` succeeds with zero TypeScript errors after cutover
- No runtime errors on any page

---

## US-FRD1: Warm Editorial Dashboard

> As a user, I want the dashboard to present a warm welcome with clear entry points to the main workflows so that I can quickly start working when I open the app.

**Acceptance Criteria**:
- Page shows welcome heading "Welcome to Manga OCR" in font-display, with tagline
- Three quick-action cards in a row: "Upload Images", "Quick Run", "OCR Playground"
- Each card has a description and a navigation button
- Recent runs section shows last 5 pipeline runs in a clean table with status badges
- Stats section shows 4 stat cards: Total Runs, Completed, Failed, Average Confidence
- Stats load from `getDashboardStats()` API
- Recent runs load from `listRuns({ limit: 5 })` API
- No DSO jargon ("Tactical Controls", "Service Matrix", "OSCILLOSCOPE CONTROL PANEL")

---

## US-FRD2: Redesigned Upload Page

> As a user, I want a spacious upload page with a large drag-and-drop area and clear profile selection so that submitting images for OCR processing is straightforward.

**Acceptance Criteria**:
- Two-column layout: left (60%) dropzone + image grid, right (40%) config
- Dropzone area has dashed border-linen, rounded-xl, cream background
- Dropzone shows indigo accent on hover and drag-over states
- Image grid shows 3-column thumbnails with remove (X) button per image
- Profile selector uses new Select component
- Submit button is Button primary "Start Processing"
- Created runs shown below with status badges
- Drag-and-drop and file picker both work

---

## US-FRD3: Redesigned Quick Run Page

> As a user, I want the Quick Run page to present a clear upload-configure-results flow so that I can quickly test OCR on a single image with full control over settings.

**Acceptance Criteria**:
- Two-column layout: left = image upload + preview, right = collapsible config panels
- Config sections in Card components: Preprocessing, OCR Models, LLM Settings
- Each section is collapsible (click header to toggle)
- "Run" button is Button primary, shown prominently
- Results appear below both columns after processing
- Results include OcrResultCard and LlmExtractionCard components
- Profile loading and YAML import still work

---

## US-FRD4: Redesigned Runs List Page

> As a user, I want a clean runs list with status filter pills so that I can quickly find runs by status and navigate to details.

**Acceptance Criteria**:
- Status filter shown as pill buttons: All / Pending / Processing / Completed / Failed
- Active filter pill has bg-indigo-pale text-indigo
- Table shows: Image (thumbnail), Status (Badge), Created timestamp, Completed timestamp
- Rows are clickable, navigating to `/runs/:id`
- Pagination at bottom of table
- Status filter pills filter the API query
- Auto-refresh (polling) still works for active runs

---

## US-FRD5: Redesigned Run Detail Page

> As a user, I want a two-column run detail page with the image on the left and results on the right so that I can see the source image alongside OCR output.

**Acceptance Criteria**:
- Two-column layout: left (40%) = large image preview, right (60%) = results
- Image preview loads from `/api/v1/pipeline/runs/{id}/image`
- Right column shows run metadata card (status Badge, created/completed timestamps)
- OCR results shown as collapsible cards per model (model name, raw text, confidence)
- Post-processing result shown in LlmExtractionCard
- Override form allows editing title_en, title_ja, code with save Button
- Override calls `PUT /api/v1/results/{result_id}/override` API
- TopBar shows "Retry" and "Cancel" action buttons when run is in appropriate status

---

## US-FRE1: Redesigned Batch List Page

> As a user, I want batches shown as cards instead of table rows so that I can see batch progress at a glance.

**Acceptance Criteria**:
- Each batch displayed as a Card with: batch name (font-display), status Badge, ProgressBar
- Card shows "X/Y completed" text and created date
- "View Details" Button ghost on each card
- "Create Batch" Button primary in TopBar actions area
- Pagination at bottom for many batches
- Cards arranged in a responsive grid (2-3 columns)

---

## US-FRE2: Redesigned Batch Detail Page

> As a user, I want batch detail to show an overview of progress and a list of individual runs so that I can monitor and manage a batch.

**Acceptance Criteria**:
- Top section: progress overview Card with ProgressBar, completed/failed/pending counts
- Below: Table of runs in batch with status badges
- "Retry Failed" Button (shown only when failed runs exist) in TopBar actions
- Clicking a run navigates to `/runs/:id`
- Progress bar updates via polling

---

## US-FRE3: Redesigned Catalog Page

> As a user, I want a searchable catalog with inline editing so that I can curate extracted manga titles efficiently.

**Acceptance Criteria**:
- Search bar (Input) filters entries by title or code via API
- Status filter pills: All / Confirmed / Needs Review / Rejected
- Table shows: title_en, title_ja, code, confidence (ProgressBar), status (Badge), date
- Click row to expand: shows inline edit form with Input fields for title_en, title_ja, code
- Save button updates entry via `PUT /api/v1/catalog/{entry_id}` API
- "Export CSV" Button secondary in TopBar actions
- Pagination for large catalogs

---

## US-FRE4: Redesigned OCR Playground

> As a user, I want the OCR playground to have a clean two-panel layout so that I can configure and run OCR tests efficiently.

**Acceptance Criteria**:
- Two-panel layout: left = upload + model selection + LLM config, right = results
- Model selection uses radio-style cards (Card with selected state = indigo border accent)
- LLM config section is collapsible using LlmConfigSection component
- Results panel shows OcrResultCard and LlmExtractionCard
- "Run OCR" Button primary triggers the OCR API call
- All model and LLM configuration options preserved from current implementation

---

## US-FRE5: Redesigned Preprocess Playground

> As a user, I want the preprocess playground to show a clear step pipeline with before/after comparison so that I can tune preprocessing settings visually.

**Acceptance Criteria**:
- Left side: image upload + horizontal step pipeline bar
- Right side: ImageCompare component for before/after view
- Step config shown below pipeline bar using PreprocessStepCard components
- Active step highlighted in the pipeline bar
- "Preview" and "Preview Pipeline" buttons use Button component
- Export config uses Button secondary

---

## US-FRE6: Redesigned Profiles Page

> As a user, I want profiles displayed in a clean table with import/export actions so that I can manage reusable pipeline configurations.

**Acceptance Criteria**:
- Table shows: name, description, default indicator (Badge), created date, action buttons (edit/delete/export)
- "New Profile" Button primary and "Import" Button secondary in TopBar actions
- Import modal uses fixed overlay with Card container
- Import modal has file input, validate button, and import button
- Set as default action updates profile via API
- Export downloads profile JSON file

---

## US-FRE7: Redesigned Profile Editor

> As a user, I want a multi-section profile editor with clear save/cancel actions so that I can create or modify pipeline configurations.

**Acceptance Criteria**:
- Stacked Card sections: Name/Description, Preprocessing, OCR, LLM
- Name section uses Input component
- Preprocessing section uses PreprocessStepCard instances
- OCR section uses OcrModelCard instances
- LLM section uses LlmConfigSection + PromptSettingsPanel
- TopBar shows "Save" Button primary and "Cancel" Button ghost
- Edit mode loads existing profile data from API on mount
- Save calls create or update API endpoint based on mode (new vs edit)
- Validation errors shown inline on Input components

---

## US-FRE8: Redesigned Settings Page

> As a user, I want a clean settings page with Ollama connection and API credential sections so that I can configure external service integrations.

**Acceptance Criteria**:
- Two Card sections: "Ollama Connection" and "API Credentials"
- Ollama section: URL Input, "Ping" Button, connection status indicator, vision/LLM model selectors
- API Credentials section: OpenRouter key Input (masked/password type), "Validate", "Save", "Delete" Buttons
- All inputs use new Input component with label and error states
- Ping and validate actions show success/error feedback
- Saved settings persist and load correctly from API

---

## US-FRF1: Consistent Loading States

> As a user, I want loading states to use subtle pulse animations instead of the old "breathing" effect so that the app feels responsive and modern.

**Acceptance Criteria**:
- All pages that load data show a loading state while fetching
- Loading states use Tailwind's animate-pulse or the new fade-pulse animation
- No "breathing" CSS class or animation referenced anywhere in the codebase
- Loading skeletons show the expected layout structure (not just a spinner)
- Loading states resolve when data arrives or an error occurs

---

## US-FRF2: Empty States for All List Pages

> As a user, I want clear empty state messages when there is no data so that I know what to do next instead of seeing a blank page.

**Acceptance Criteria**:
- Runs page: shows EmptyState "No pipeline runs yet" with Upload button
- Batches page: shows EmptyState "No batch runs" with Create Batch button
- Catalog page: shows EmptyState "No catalog entries" with description
- Profiles page: shows EmptyState "No profiles" with Create Profile button
- EmptyState component used consistently: icon + title + description + action
- Empty state is replaced by data when API returns results

---

## US-FRF3: Page Transition Animations

> As a user, I want subtle fade-in animations when navigating between pages so that transitions feel smooth rather than jarring.

**Acceptance Criteria**:
- Main content area has animate-fade-in class
- Page transitions use a 0.15s ease-out fade-in animation
- Animation does not delay content rendering (starts immediately)
- Animation works on all route changes

---

## US-FRF4: Consistent Hover and Focus States

> As a user, I want all interactive elements to provide clear visual feedback on hover and focus so that I can tell what is clickable and where my keyboard focus is.

**Acceptance Criteria**:
- All buttons show visible hover state (bg change)
- All buttons show focus-visible ring (2px indigo outline, 2px offset)
- All inputs and selects show indigo focus ring on focus
- All table rows with onRowClick show hover:bg-cream/50
- All nav items in sidebar show hover:bg-cream
- Focus states are keyboard-accessible (focus-visible, not focus)
- Active/pressed state for buttons: scale-[0.98]

---

## US-FRF5: No DSO Remnants

> As a user, I want zero visual or code remnants of the old oscilloscope/DSO design so that the app feels completely redesigned.

**Acceptance Criteria**:
- No DSO CSS class names in any source file (neo-panel, neo-inset, lcd-screen, led, tech-label, breathing, haptic-snap, neo-press, lcd-graticule, scanline-sweep)
- No DSO color token names in any source file (chassis, panel, lcd, teal, amber, bright, muted, highlight, panel-light, surface-dark, teal-dim, teal-glow, amber-dim, amber-glow)
- No `components/dso/` directory or files
- No visual artifacts resembling oscilloscope aesthetic (scanlines, LED indicators, screw decorations, vent grilles)
- `make frontend-lint` passes with zero errors
- `make frontend-format` passes with zero changes needed
- `npm run build` succeeds with zero errors
