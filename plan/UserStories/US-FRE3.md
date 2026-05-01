# US-FRE3: Redesigned Catalog Page

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want a searchable catalog with inline editing so that I can curate extracted manga titles efficiently.

---

## Scope

### In Scope
- Rewrite Catalog.tsx with search bar, status filter pills, expandable table rows
- Inline edit form for title_en, title_ja, code
- "Export CSV" button in TopBar actions
- Pagination

### Out of Scope
- Bulk edit operations
- Loading skeletons (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/Catalog.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ TopBar: [Catalog]                    [Export CSV]│
├─────────────────────────────────────────────────┤
│ Search: [________________________]               │
│ Filter: [All] [Confirmed] [Needs Review] [Rej.] │
│                                                  │
│ ┌──────────┬──────────┬──────┬────┬──────┬────┐ │
│ │title_en  │title_ja  │code  │conf│status│date│ │
│ ├──────────┼──────────┼──────┼────┼──────┼────┤ │
│ │One Piece │ワンピース │OP-001│87% │Conf. │2m  │ │
│ │  [edit form expanded below]                   │ │
│ │  title_en: [One Piece___]                     │ │
│ │  title_ja: [ワンピース____]                     │ │
│ │  code:     [OP-001______]                     │ │
│ │  [Save] [Cancel]                              │ │
│ ├──────────┼──────────┼──────┼────┼──────┼────┤ │
│ │Naruto    │ナルト     │NR-001│92% │Review│5m  │ │
│ └──────────┴──────────┴──────┴────┴──────┴────┘ │
│                                                  │
│              1–20 of 150  [Prev] [Next]          │
└─────────────────────────────────────────────────┘
```

**Search bar:** `<Input>` with placeholder "Search by title or code..."

**Status filter pills:** All / Confirmed (auto_confirmed) / Needs Review / Rejected

**Table columns:**
- title_en (text)
- title_ja (text, font-japanese)
- code (text)
- confidence (ProgressBar)
- status (Badge: auto_confirmed → completed, needs_review → review, rejected → failed)
- date (formatted)

**Inline edit:** Click row to expand edit form:
```tsx
{expandedId === entry.id && (
  <tr>
    <td colSpan={6} className="bg-cream/50 px-4 py-3">
      <div className="grid grid-cols-3 gap-3">
        <Input label="Title (EN)" value={editForm.title_en} onChange={...} />
        <Input label="Title (JA)" value={editForm.title_ja} onChange={...} />
        <Input label="Code" value={editForm.code} onChange={...} />
      </div>
      <div className="flex gap-2 mt-3">
        <Button variant="primary" size="sm" onClick={handleSave}>Save</Button>
        <Button variant="ghost" size="sm" onClick={handleCancel}>Cancel</Button>
      </div>
    </td>
  </tr>
)}
```

**Export CSV:** TopBar action: `<Button variant="secondary" size="sm">Export CSV</Button>` linking to `getCatalogExportUrl()`

---

## Acceptance Criteria

- [ ] Search Input filters entries by title or code via API `search` parameter
- [ ] Status filter pills: All / Confirmed / Needs Review / Rejected
- [ ] Table shows: title_en, title_ja, code, confidence (ProgressBar), status (Badge), date
- [ ] Click row to expand inline edit form with Input fields
- [ ] Save button calls `PUT /api/v1/catalog/{entry_id}` API
- [ ] "Export CSV" Button secondary in TopBar actions
- [ ] Pagination for large catalogs
- [ ] Japanese text renders in Noto Sans JP

---

## Validation

1. Screenshot Catalog — verify search bar, filter pills, table
2. Type in search — verify filtered results
3. Click a row — verify inline edit form expands
4. Edit and save — verify API call and updated data
