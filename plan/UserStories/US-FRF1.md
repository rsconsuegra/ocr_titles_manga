# US-FRF1: Consistent Loading States

**Sub-phase**: FR-F — Polish
**Depends on**: US-FRD1–D5 (core pages), US-FRE1–E8 (secondary pages)
**Blocks**: US-FRF5 (final cleanup)

---

## Story

> As a user, I want loading states to use subtle pulse animations instead of the old "breathing" effect so that the app feels responsive and modern.

---

## Scope

### In Scope
- Add loading skeletons to all data-fetching pages
- Replace any "breathing" class references with animate-pulse or fade-pulse
- Skeleton layout matches expected page structure

### Out of Scope
- New features
- Empty states (US-FRF2)

---

## Implementation Details

### Skeleton Pattern

Each page that fetches data should show a loading skeleton matching its layout:

```tsx
function Skeleton({ className }: { className?: string }) {
  return <div className={`bg-linen rounded animate-pulse ${className || ""}`} />;
}

function DashboardSkeleton() {
  return (
    <div>
      <Skeleton className="h-8 w-64 mb-2" />
      <Skeleton className="h-4 w-96 mb-8" />
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[1, 2, 3].map((i) => (
          <Card key={i}><Skeleton className="h-20" /></Card>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}><Skeleton className="h-16" /></Card>
        ))}
      </div>
      <Card><Skeleton className="h-40" /></Card>
    </div>
  );
}
```

### Pages requiring loading states

| Page | Skeleton Layout |
|------|-----------------|
| Dashboard | Welcome text + 3 action cards + 4 stat cards + table |
| Runs | Filter pills + 5 table rows |
| RunDetail | 2-column: image placeholder + 3 result cards |
| BatchRuns | 3 batch cards |
| BatchRunDetail | Progress card + 5 table rows |
| Catalog | Search bar + filter pills + 5 table rows |
| Profiles | 5 table rows |
| OcrPlayground | 2-panel: config cards + results placeholder |
| PreprocessPlayground | 2-panel: step bar + image placeholder |
| QuickRun | 2-column: image placeholder + config cards |
| Settings | 2 stacked cards |

### Implementation per page

```tsx
export default function Page() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchData().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSkeleton />;
  return <ActualContent data={data} />;
}
```

---

## Acceptance Criteria

- [ ] All pages that load data show a loading state while fetching
- [ ] Loading states use `animate-pulse` (not "breathing" CSS class)
- [ ] Skeleton layouts match expected page structure
- [ ] Loading states resolve when data arrives or error occurs
- [ ] No "breathing" CSS class or animation referenced anywhere
- [ ] Skeletons use `bg-linen rounded animate-pulse` pattern
- [ ] Consistent skeleton height/spacing across all pages

---

## Validation

1. Open Dashboard with slow network (DevTools throttling) — verify skeleton appears before data
2. Check that skeleton shapes match the final layout structure
3. Verify no visible "breathing" animation anywhere
