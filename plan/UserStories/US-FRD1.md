# US-FRD1: Warm Editorial Dashboard

**Sub-phase**: FR-D — Core Pages
**Depends on**: US-FRC7 (DSO removed, new components available)
**Blocks**: US-FRF1 (loading states), US-FRF2 (empty states)

---

## Story

> As a user, I want the dashboard to present a warm welcome with clear entry points to the main workflows so that I can quickly start working when I open the app.

---

## Scope

### In Scope
- Rewrite Dashboard.tsx with welcome heading, quick-action cards, stats grid, recent runs
- Uses new Card, Button, Badge, Table, ProgressBar, EmptyState components
- Loads data from `getDashboardStats()` and `listRuns({ limit: 5 })` APIs

### Out of Scope
- Loading skeletons (US-FRF1)
- Empty state for no data (US-FRF2)

---

## Implementation Details

### 1. `frontend/src/pages/Dashboard.tsx` (rewritten)

Layout structure:
```
┌─────────────────────────────────────────────────┐
│ Welcome to Manga OCR                             │
│ Extract and catalog manga titles with OCR        │
├──────────────┬──────────────┬───────────────────┤
│ Upload Images│  Quick Run   │  OCR Playground   │
│ description  │  description │  description      │
│ [Go →]       │  [Go →]      │  [Go →]           │
├──────────────┴──────────────┴───────────────────┤
│ Stats                                            │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐     │
│ │Total   │ │Complete│ │Failed  │ │Avg Conf│     │
│ │  42    │ │  38    │ │   2    │ │  87%   │     │
│ └────────┘ └────────┘ └────────┘ └────────┘     │
├─────────────────────────────────────────────────┤
│ Recent Runs                          [View All→] │
│ ┌──────┬──────────┬──────────┬──────────┐        │
│ │Img   │Status    │Created   │Completed │        │
│ ├──────┼──────────┼──────────┼──────────┤        │
│ │[img] │Completed │ 2m ago   │ 1m ago   │        │
│ │[img] │Processing│ 5m ago   │ -        │        │
│ └──────┴──────────┴──────────┴──────────┘        │
└─────────────────────────────────────────────────┘
```

Key implementation:

```tsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Card, Button, Badge, Table, ProgressBar, EmptyState } from "../components/ui";
import type { Column } from "../components/ui/Table";
import { getDashboardStats, listRuns } from "../api/client";

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<any>(null);
  const [recentRuns, setRecentRuns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, r] = await Promise.all([
          getDashboardStats(),
          listRuns({ limit: 5 }),
        ]);
        setStats(s);
        setRecentRuns(r.items || []);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // ... render sections below
}
```

### Sections

**Welcome section:**
- `<h1 className="font-display text-2xl font-semibold text-ink mb-2">Welcome to Manga OCR</h1>`
- `<p className="text-sand font-body text-sm">Extract and catalog manga titles with OCR</p>`

**Quick-action cards:** `grid grid-cols-3 gap-4`
- Each card: `<Card hover>` with title, description, and Button ghost "Go →"
- Cards: "Upload Images" (→/run/pipeline), "Quick Run" (→/run/quick), "OCR Playground" (→/playground/ocr)

**Stats grid:** `grid grid-cols-4 gap-4`
- Each stat: `<Card padding="sm">` with label-text stat name and large number
- Stats: Total Runs, Completed, Failed, Average Confidence (with ProgressBar)

**Recent runs:** `<Card>` with `Card.Header title="Recent Runs"` and ghost "View All →" action
- Table with columns: Image (thumbnail), Status (Badge), Created, Completed
- If no runs: EmptyState "No recent runs" with Upload action

---

## Acceptance Criteria

- [ ] Page shows "Welcome to Manga OCR" heading in font-display
- [ ] Tagline text below heading in sand color
- [ ] Three quick-action cards in a row: Upload Images, Quick Run, OCR Playground
- [ ] Each card navigates to correct route on button click
- [ ] Stats section shows 4 cards: Total Runs, Completed, Failed, Avg Confidence
- [ ] Stats load from `getDashboardStats()` API
- [ ] Recent runs section shows last 5 runs in a Table with status Badges
- [ ] Recent runs load from `listRuns({ limit: 5 })` API
- [ ] "View All" link in recent runs header navigates to /runs
- [ ] No DSO jargon text ("Tactical Controls", "Service Matrix", "OSCILLOSCOPE")
- [ ] All text uses font-body or font-display (no tech-label references)

---

## Validation

1. Screenshot Dashboard — verify warm editorial feel
2. Click each quick-action card — verify navigation
3. Stats show numbers from API (or 0 if API unavailable)
4. Recent runs table shows status badges with correct colors
