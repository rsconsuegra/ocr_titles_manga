# US-FRE1: Redesigned Batch List Page

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want batches shown as cards instead of table rows so that I can see batch progress at a glance.

---

## Scope

### In Scope
- Rewrite BatchRuns.tsx with card grid layout
- Each card shows batch name, status Badge, ProgressBar, completed count
- "View Details" ghost button on each card
- Pagination for many batches

### Out of Scope
- Creating batches (done via Upload page)
- Loading skeletons (US-FRF1)
- Empty state (US-FRF2)

---

## Implementation Details

### 1. `frontend/src/pages/BatchRuns.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│ │ Batch Alpha │ │ Batch Beta  │ │ Batch Gamma ││
│ │ [Completed] │ │ [Processing]│ │ [Pending]   ││
│ │ ████░░ 80%  │ │ ██░░░░ 40%  │ │ ░░░░░░  0%  ││
│ │ 8/10 done   │ │ 4/10 done   │ │ 0/5 done    ││
│ │ 2h ago      │ │ 5m ago      │ │ Just now    ││
│ │ [View →]    │ │ [View →]    │ │ [View →]    ││
│ └─────────────┘ └─────────────┘ └─────────────┘│
│                                                  │
│              1–9 of 9  [Prev] [Next]             │
└─────────────────────────────────────────────────┘
```

**Card grid:** `grid grid-cols-3 gap-4`

Each batch card:
```tsx
<Card hover>
  <h3 className="font-display text-lg font-semibold text-ink mb-2">
    {batch.name || `Batch ${batch.id.slice(0, 8)}`}
  </h3>
  <div className="mb-3">
    <Badge status={mapBatchStatus(batch.status)} />
  </div>
  <ProgressBar value={completionPercent} size="sm" className="mb-2" />
  <p className="text-sm text-sand font-body">
    {completed}/{total} completed
  </p>
  <p className="text-xs text-sand font-body mt-1">
    {formatDate(batch.created_at)}
  </p>
  <div className="mt-3">
    <Button variant="ghost" size="sm" onClick={() => navigate(`/batches/${batch.id}`)}>
      View Details →
    </Button>
  </div>
</Card>
```

**Status mapping:** `pending` → pending, `processing` → processing, `completed` → completed, `failed` → failed, `partial_failure` → review

---

## Acceptance Criteria

- [ ] Batches displayed as Cards in `grid-cols-3` grid
- [ ] Each card shows: batch name (font-display), status Badge, ProgressBar
- [ ] Each card shows "X/Y completed" text and created date
- [ ] "View Details" ghost Button on each card navigates to `/batches/:id`
- [ ] Pagination at bottom for many batches
- [ ] Cards arranged in responsive grid

---

## Validation

1. Screenshot Batches page — verify card grid layout
2. Verify ProgressBar colors match completion percentages
3. Click "View Details" — verify navigation to batch detail
