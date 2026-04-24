# US-1D4: Browse Catalog in UI

**Sub-phase**: 1D — Frontend
**Depends on**: US-1B6 (catalog API), US-1D2 (shared components: ConfidenceMeter, RunStatusBadge pattern)
**Blocks**: None

---

## Overview

Create the catalog page for browsing, searching, filtering, and editing extracted manga titles. Includes CSV export functionality.

---

## Implementation Details

### 1. `frontend/src/api/client.ts` additions

```typescript
export interface CatalogEntryResponse {
  id: string;
  title_en: string | null;
  title_ja: string | null;
  code: string | null;
  source_run_id: string;
  confidence: number;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export async function listCatalog(params?: {
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<CatalogEntryResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/catalog${qs ? `?${qs}` : ""}`);
}

export async function updateCatalogEntry(
  entryId: string,
  data: { status?: string; title_en?: string; title_ja?: string; code?: string }
): Promise<CatalogEntryResponse> {
  return apiFetch<CatalogEntryResponse>(`/api/v1/catalog/${entryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function getCatalogExportUrl(): string {
  const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
  return `${base}/api/v1/catalog/export`;
}
```

### 2. `frontend/src/pages/Catalog.tsx`

Page layout:

**Header section**:
- Title: "Catalog"
- "Export CSV" button (downloads from API)
- Search input: placeholder "Search title or code..."
- Status filter dropdown: All / Auto Confirmed / Needs Review / Rejected

**Table**:
Columns: Title EN, Title JA, Code, Confidence, Status, Created At
- Each row clickable to expand inline edit panel
- Confidence rendered as `ConfidenceMeter` component
- Status rendered as colored badge (matching `RunStatusBadge` pattern)

**Expanded row**:
- Editable fields: Title EN (input), Title JA (input), Code (input)
- Status dropdown: Auto Confirmed / Needs Review / Rejected
- "Save" button
- Source run link: `/runs/:source_run_id`
- "Collapse" button

**Pagination**: Same pattern as Runs page

State:
```typescript
const [entries, setEntries] = useState<CatalogEntryResponse[]>([]);
const [total, setTotal] = useState(0);
const [offset, setOffset] = useState(0);
const [statusFilter, setStatusFilter] = useState<string>("");
const [search, setSearch] = useState("");
const [searchDebounced, setSearchDebounced] = useState("");
const [expandedId, setExpandedId] = useState<string | null>(null);
const [editForm, setEditForm] = useState({ title_en: "", title_ja: "", code: "", status: "" });
const [saving, setSaving] = useState(false);
const limit = 20;
```

Search debounce (300ms):
```typescript
useEffect(() => {
  const timer = setTimeout(() => setSearchDebounced(search), 300);
  return () => clearTimeout(timer);
}, [search]);
```

Data fetching:
```typescript
useEffect(() => {
  listCatalog({
    status: statusFilter || undefined,
    search: searchDebounced || undefined,
    limit,
    offset,
  }).then(data => { setEntries(data.items); setTotal(data.total); });
}, [statusFilter, searchDebounced, offset]);
```

CSV export:
```typescript
function handleExport() {
  window.open(getCatalogExportUrl(), "_blank");
}
```

Inline edit:
```typescript
function handleExpand(entry: CatalogEntryResponse) {
  setExpandedId(entry.id);
  setEditForm({
    title_en: entry.title_en || "",
    title_ja: entry.title_ja || "",
    code: entry.code || "",
    status: entry.status,
  });
}

async function handleSave() {
  if (!expandedId) return;
  setSaving(true);
  await updateCatalogEntry(expandedId, editForm);
  setSaving(false);
  setExpandedId(null);
  // Refresh list
  const data = await listCatalog({ status: statusFilter || undefined, search: searchDebounced || undefined, limit, offset });
  setEntries(data.items);
  setTotal(data.total);
}
```

---

## Acceptance Criteria

- [ ] `/catalog` page renders with catalog table
- [ ] Search input filters entries by title and code (debounced 300ms)
- [ ] Status filter dropdown filters by status
- [ ] Confidence meters shown per entry (color-coded)
- [ ] Status badges color-coded per status
- [ ] Click row expands inline edit panel
- [ ] Edit fields pre-filled with current values
- [ ] "Save" updates entry via API and refreshes table
- [ ] Status dropdown in edit panel works
- [ ] Source run link navigates to `/runs/:id`
- [ ] "Export CSV" downloads CSV file
- [ ] Pagination works (same pattern as Runs page)
- [ ] Empty state: "No catalog entries yet" message
- [ ] Combined search + status filter works

---

## Expected Views

**Empty state**: "No catalog entries yet. Upload images and run the pipeline to populate the catalog."

**With entries**: Full-width table. Each row: Title EN (or "—"), Title JA (or "—"), Code (or "—"), confidence bar, status badge, relative timestamp.

**Expanded row**: Below the clicked row. Gray background panel. Three text inputs + status dropdown + Save button. "Source: Run #abc12345" link.

**Filter bar**: Search input (left), Status dropdown (center), Export CSV button (right).

---

## Test Specifications

Manual testing checklist:
- [ ] Empty catalog: shows empty state message
- [ ] With entries: table renders with correct data
- [ ] Search by title: results filter as you type (debounced)
- [ ] Search by code/ISBN: results filter correctly
- [ ] Filter by "Needs Review": only matching entries
- [ ] Expand row: edit panel appears with pre-filled values
- [ ] Edit title + save: table updates with new value
- [ ] Change status + save: badge updates
- [ ] Export CSV: file downloads with correct content
- [ ] Click source run link: navigates to run detail
- [ ] Pagination: navigates correctly
- [ ] Clear search: all entries shown again
