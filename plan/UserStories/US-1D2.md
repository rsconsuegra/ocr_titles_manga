# US-1D2: View Pipeline Run History in UI

**Sub-phase**: 1D — Frontend
**Depends on**: US-1B3 (list runs API), US-1D1 (shared components: RunStatusBadge)
**Blocks**: None

---

## Overview

Create the runs list page showing all pipeline runs with status badges, filtering, and pagination. Clicking a run navigates to the detail page.

---

## Implementation Details

### 1. `frontend/src/api/client.ts` additions

```typescript
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export async function listRuns(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<PipelineRunResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/pipeline/runs${qs ? `?${qs}` : ""}`);
}
```

### 2. `frontend/src/components/RunStatusBadge.tsx`

Props: `status: string`

```typescript
const STATUS_STYLES: Record<string, string> = {
  pending: "bg-gray-100 text-gray-700",
  processing: "bg-blue-100 text-blue-700",
  completed: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};
```

Renders a small pill/badge with the status text and appropriate color class.

### 3. `frontend/src/pages/Runs.tsx`

Page layout:
- Title: "Pipeline Runs"
- Status filter dropdown: All / Pending / Processing / Completed / Failed
- Table: Run ID (truncated, first 8 chars with full UUID in tooltip), Image Path, Status Badge, Created At, Completed At
- Pagination: "Previous" / "Next" buttons with "Showing X-Y of Z" text
- Click row -> navigate to `/runs/:id`

State:
```typescript
const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
const [total, setTotal] = useState(0);
const [offset, setOffset] = useState(0);
const [statusFilter, setStatusFilter] = useState<string>("");
const [loading, setLoading] = useState(true);
const limit = 20;
```

Data fetching:
```typescript
useEffect(() => {
  setLoading(true);
  listRuns({ status: statusFilter || undefined, limit, offset })
    .then(data => { setRuns(data.items); setTotal(data.total); })
    .finally(() => setLoading(false));
}, [statusFilter, offset]);
```

Auto-refresh: poll every 10 seconds while any run has status "pending" or "processing":
```typescript
useEffect(() => {
  const hasActive = runs.some(r => r.status === "pending" || r.status === "processing");
  if (!hasActive) return;
  const interval = setInterval(() => {
    listRuns({ status: statusFilter || undefined, limit, offset })
      .then(data => { setRuns(data.items); setTotal(data.total); });
  }, 10000);
  return () => clearInterval(interval);
}, [runs, statusFilter, offset]);
```

---

## Acceptance Criteria

- [ ] `/runs` page renders with empty state or run table
- [ ] Each run shows: truncated ID, image path, status badge (color-coded), timestamps
- [ ] Status filter dropdown filters visible runs
- [ ] Pagination shows "Showing 1-20 of 42" text
- [ ] Previous/Next buttons work correctly
- [ ] Click a run row navigates to `/runs/:id`
- [ ] Auto-refreshes every 10s when active runs exist
- [ ] Loading state shown while fetching
- [ ] Empty state: "No pipeline runs yet" message

---

## Expected Views

**Empty state**: Centered text "No pipeline runs yet" with link to upload page.

**With runs**: Full-width table with columns: Run ID, Image, Status, Created, Completed. Each row clickable (cursor-pointer, hover:bg-gray-50).

**Filter bar**: Dropdown "Status: All ▾" next to title. Pagination at bottom.

---

## Test Specifications

Manual testing checklist:
- [ ] Empty DB: shows empty state message
- [ ] With runs: table renders with correct data
- [ ] Filter by "Completed": only completed runs shown
- [ ] Filter by "Failed": only failed runs shown
- [ ] Pagination: next/previous navigate correctly
- [ ] Click row: navigates to `/runs/:id`
- [ ] Active runs: auto-refresh visible (status changes without manual refresh)
