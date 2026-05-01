# US-FRD4: Redesigned Runs List Page

**Sub-phase**: FR-D — Core Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want a clean runs list with status filter pills so that I can quickly find runs by status and navigate to details.

---

## Scope

### In Scope
- Rewrite Runs.tsx with status filter pills
- Clean table with status badges
- Pagination
- Auto-refresh polling for active runs

### Out of Scope
- Loading skeletons (US-FRF1)
- Empty state (US-FRF2)

---

## Implementation Details

### 1. `frontend/src/pages/Runs.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ Filter: [All] [Pending] [Processing] [Completed]│
│                                       [Failed]  │
├─────────────────────────────────────────────────┤
│ ┌──────┬──────────┬──────────┬──────────┐       │
│ │Image │Status    │Created   │Completed │       │
│ ├──────┼──────────┼──────────┼──────────┤       │
│ │[img] │Completed │ 2m ago   │ 1m ago   │       │
│ │[img] │Processing│ 5m ago   │ -        │       │
│ └──────┴──────────┴──────────┴──────────┘       │
│                                                  │
│              1–20 of 42  [Prev] [Next]           │
└─────────────────────────────────────────────────┘
```

**Status filter pills:**
```tsx
const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

// Render:
<div className="flex gap-2 mb-6">
  {STATUS_FILTERS.map((f) => (
    <button
      key={f.value}
      onClick={() => setStatusFilter(f.value)}
      className={`
        px-3 py-1.5 rounded-full text-sm font-body font-medium transition-colors
        ${statusFilter === f.value
          ? "bg-indigo-pale text-indigo"
          : "bg-snow text-charcoal border border-linen hover:bg-cream"}
      `}
    >
      {f.label}
    </button>
  ))}
</div>
```

**Table columns:**
- Image: 48x48 thumbnail (from `/api/v1/pipeline/runs/{id}/image` or placeholder)
- Status: Badge component
- Created: formatted timestamp
- Completed: formatted timestamp or "—"

**Pagination:** Uses Pagination component at bottom

**Auto-refresh:** `useEffect` with `setInterval(5000)` when any run has status "pending" or "processing"

---

## Acceptance Criteria

- [ ] Status filter shown as pill buttons: All, Pending, Processing, Completed, Failed
- [ ] Active filter pill: bg-indigo-pale text-indigo
- [ ] Inactive pills: bg-snow text-charcoal border-linen
- [ ] Table shows: Image (thumbnail), Status (Badge), Created, Completed
- [ ] Rows clickable → navigate to `/runs/:id`
- [ ] Pagination at bottom of table
- [ ] Filter pills update API query (`status` parameter)
- [ ] Auto-refresh (5s polling) when active runs exist
- [ ] Polling stops when no active runs

---

## Validation

1. Screenshot Runs page — verify filter pills and table
2. Click "Failed" filter — verify only failed runs shown
3. Click a run row — verify navigation to run detail
4. Verify pagination shows correct count
