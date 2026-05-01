# US-FRE6: Redesigned Profiles Page

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want profiles displayed in a clean table with import/export actions so that I can manage reusable pipeline configurations.

---

## Scope

### In Scope
- Rewrite Profiles.tsx with clean table + action buttons
- Import modal with Card container
- Export, set default, delete actions

### Out of Scope
- Profile editor (US-FRE7)
- Loading skeletons (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/Profiles.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ TopBar: [Profiles]     [New Profile] [Import]   │
├─────────────────────────────────────────────────┤
│ ┌──────────┬───────────┬───────┬──────┬───────┐ │
│ │Name      │Description│Default│Created│Actions│ │
│ ├──────────┼───────────┼───────┼──────┼───────┤ │
│ │Standard  │Default OCR│[Yes]  │2d ago│⚙ ⬇ 🗑│ │
│ │High Qual │4x upscale│       │1d ago│⚙ ⬇ 🗑│ │
│ └──────────┴───────────┴───────┴──────┴───────┘ │
│                                                  │
│              1–5 of 5  [Prev] [Next]             │
│                                                  │
│ ┌─ Import Modal (overlay) ───────────────────┐  │
│ │  Import Profile                             │  │
│ │  [Choose file...]                           │  │
│ │  [Validate] [Import]                        │  │
│ └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

**TopBar actions:** "New Profile" Button primary + "Import" Button secondary

**Table columns:**
- Name (text, font-body font-medium)
- Description (text, text-sand)
- Default (Badge: "default" status if is_default, else empty)
- Created (formatted date)
- Actions: Edit (ghost), Export (ghost), Delete (danger ghost), Set Default (ghost)

**Import modal:**
```tsx
{showImportModal && (
  <div className="fixed inset-0 bg-ink/20 flex items-center justify-center z-50">
    <Card padding="lg" className="w-full max-w-md">
      <Card.Header title="Import Profile" />
      <input type="file" accept=".json" onChange={handleFileSelect} className="mb-4" />
      <div className="flex gap-2 justify-end">
        <Button variant="ghost" onClick={() => setShowImportModal(false)}>Cancel</Button>
        <Button variant="secondary" onClick={handleValidate} disabled={!file}>Validate</Button>
        <Button variant="primary" onClick={handleImport} disabled={!validated}>Import</Button>
      </div>
    </Card>
  </div>
)}
```

---

## Acceptance Criteria

- [ ] Table shows: name, description, default indicator (Badge), created date, action buttons
- [ ] "New Profile" Button primary in TopBar → navigates to `/profiles/new`
- [ ] "Import" Button secondary in TopBar → opens import modal
- [ ] Import modal: fixed overlay with Card, file input, Validate + Import buttons
- [ ] Validate calls `validateProfileImport` API
- [ ] Import calls `importProfile` API
- [ ] Export downloads profile JSON file
- [ ] Set as default calls `setDefaultProfile` API
- [ ] Delete calls `deleteProfile` API with confirmation

---

## Validation

1. Screenshot Profiles — verify table with action buttons
2. Click "New Profile" — verify navigation to editor
3. Click "Import" — verify modal opens
4. Verify import validate → import flow
