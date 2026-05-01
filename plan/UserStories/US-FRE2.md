# US-FRE2: Redesigned Batch Detail Page

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want batch detail to show an overview of progress and a list of individual runs so that I can monitor and manage a batch.

---

## Scope

### In Scope
- Rewrite BatchRunDetail.tsx with progress overview + runs table
- "Retry Failed" button in TopBar actions
- Clickable runs navigating to run detail
- Polling for active batches

### Out of Scope
- Loading skeletons (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/BatchRunDetail.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ TopBar: [Batch Detail]          [Retry Failed]  │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ Progress Overview                            │ │
│ │ ████████░░░░ 65%                             │ │
│ │ [Completed: 5] [Failed: 1] [Pending: 2]     │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌──────┬──────────┬──────────┬──────────┐       │
│ │Img   │Status    │Created   │Completed │       │
│ ├──────┼──────────┼──────────┼──────────┤       │
│ │[img] │Completed │ 2m ago   │ 1m ago   │       │
│ │[img] │Failed    │ 5m ago   │ 6m ago   │       │
│ └──────┴──────────┴──────────┴──────────┘       │
└─────────────────────────────────────────────────┘
```

**Progress overview card:**
```tsx
<Card>
  <Card.Header title="Progress Overview" />
  <ProgressBar value={completionPercent} showLabel className="mb-4" />
  <div className="flex gap-4">
    <div className="flex items-center gap-2">
      <Badge status="completed" size="sm" /> <span className="text-sm font-body">{completed} completed</span>
    </div>
    <div className="flex items-center gap-2">
      <Badge status="failed" size="sm" /> <span className="text-sm font-body">{failed} failed</span>
    </div>
    <div className="flex items-center gap-2">
      <Badge status="pending" size="sm" /> <span className="text-sm font-body">{pending} pending</span>
    </div>
  </div>
</Card>
```

**Runs table:** Table with columns: Image, Status (Badge), Created, Completed; `onRowClick` navigates to `/runs/:id`

**TopBar actions:** "Retry Failed" Button secondary — shown only when failed > 0

**Polling:** `setInterval(3000)` when batch status is "pending" or "processing"

---

## Acceptance Criteria

- [ ] Top section: progress overview Card with ProgressBar and status counts
- [ ] Below: Table of runs with status Badges, clickable to `/runs/:id`
- [ ] "Retry Failed" Button in TopBar (visible only when failed runs exist)
- [ ] Clicking a run navigates to `/runs/:id`
- [ ] Progress updates via polling (3s interval) for active batches
- [ ] Polling stops when batch is completed/failed

---

## Validation

1. Screenshot BatchDetail — verify progress overview and runs table
2. Verify "Retry Failed" button only appears when failed > 0
3. Click a run row — verify navigation to run detail
