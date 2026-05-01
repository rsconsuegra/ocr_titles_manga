# US-FRF2: Empty States for All List Pages

**Sub-phase**: FR-F — Polish
**Depends on**: US-FRC6 (EmptyState component), US-FRD1–D5, US-FRE1–E8
**Blocks**: US-FRF5 (final cleanup)

---

## Story

> As a user, I want clear empty state messages when there is no data so that I know what to do next instead of seeing a blank page.

---

## Scope

### In Scope
- Add EmptyState component to all list/data pages
- Each empty state has title, description, and action button pointing to next step

### Out of Scope
- Loading states (US-FRF1)
- New features

---

## Implementation Details

### Empty state specifications per page

| Page | Title | Description | Action Label | Action Route |
|------|-------|-------------|-------------|-------------|
| Runs | "No pipeline runs yet" | "Upload images and run OCR to see results here" | "Upload Images" | `/run/pipeline` |
| BatchRuns | "No batch runs" | "Create a batch to process multiple images at once" | "Create Batch" | `/run/pipeline` |
| Catalog | "No catalog entries" | "Run OCR on manga images to populate the catalog" | (none) | — |
| Profiles | "No profiles" | "Create a profile to save reusable pipeline configurations" | "Create Profile" | `/profiles/new` |
| Dashboard recent runs | "No recent runs" | "Upload images to get started" | "Upload Images" | `/run/pipeline` |

### Implementation pattern

```tsx
if (!loading && data.length === 0) {
  return (
    <EmptyState
      title="No pipeline runs yet"
      description="Upload images and run OCR to see results here"
      actionLabel="Upload Images"
      onAction={() => navigate("/run/pipeline")}
    />
  );
}
```

---

## Acceptance Criteria

- [ ] Runs page: EmptyState with "Upload Images" action → /run/pipeline
- [ ] BatchRuns page: EmptyState with "Create Batch" action → /run/pipeline
- [ ] Catalog page: EmptyState with description (no action button)
- [ ] Profiles page: EmptyState with "Create Profile" action → /profiles/new
- [ ] Dashboard recent runs: EmptyState with "Upload Images" action
- [ ] EmptyState component used consistently: icon slot + title + description + action
- [ ] Empty state is replaced by data when API returns results
- [ ] Empty states don't appear during loading (loading skeleton shown first)

---

## Validation

1. Open each list page with no data — verify empty state message with correct action
2. Click action button — verify navigation to correct route
3. Add data and return — verify empty state is replaced by data
