# US-FRD2: Redesigned Upload Page

**Sub-phase**: FR-D — Core Pages
**Depends on**: US-FRC7 (DSO removed, new components)
**Blocks**: None

---

## Story

> As a user, I want a spacious upload page with a large drag-and-drop area and clear profile selection so that submitting images for OCR processing is straightforward.

---

## Scope

### In Scope
- Rewrite Upload.tsx with two-column layout
- Dropzone with indigo hover/dragover states
- Profile selector with new Select component
- Image grid with remove buttons

### Out of Scope
- Batch mode toggle (keep existing behavior)
- Loading skeletons (US-FRF1)

---

## Implementation Details

### 1. `frontend/src/pages/Upload.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ ┌─────────────────────┐ ┌─────────────────────┐ │
│ │                     │ │  Configuration      │ │
│ │   Drop images here  │ │                     │ │
│ │   or click to browse│ │  Profile: [Select ▾]│ │
│ │                     │ │                     │ │
│ │ ┌───┐ ┌───┐ ┌───┐  │ │  [Start Processing] │ │
│ │ │img│ │img│ │img│  │ │                     │ │
│ │ │ × │ │ × │ │ × │  │ └─────────────────────┘ │
│ │ └───┘ └───┘ └───┘  │                         │
│ └─────────────────────┘                         │
│                                                  │
│ Created Runs                                     │
│ ┌──────┬──────────┬──────────┐                   │
│ │Img   │Status    │Created   │                   │
│ └──────┴──────────┴──────────┘                   │
└─────────────────────────────────────────────────┘
```

Key elements:

**Two-column layout:** `grid grid-cols-5 gap-6`
- Left `col-span-3`: dropzone + image grid
- Right `col-span-2`: configuration card

**Dropzone:**
```tsx
<div
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
  onClick={() => fileInputRef.current?.click()}
  className={`
    border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
    ${isDragging ? "border-indigo bg-indigo-pale/20" : "border-linen bg-cream hover:border-indigo/50"}
  `}
>
  <p className="text-charcoal font-body">Drop images here</p>
  <p className="text-sand font-body text-sm mt-1">or click to browse</p>
</div>
```

**Image grid:** `grid grid-cols-3 gap-3` with thumbnail + X remove button per image

**Config card:** `<Card>` with profile Select and Button primary "Start Processing"

**Created runs:** Table showing submitted runs with status Badges

---

## Acceptance Criteria

- [ ] Two-column layout: left (60%) dropzone + images, right (40%) config
- [ ] Dropzone has dashed border-linen, rounded-xl, cream background
- [ ] Dropzone shows indigo border + indigo-pale bg on drag-over
- [ ] Dropzone shows indigo/50 border on hover
- [ ] Image grid shows 3-column thumbnails with X remove button
- [ ] Profile selector uses Select component
- [ ] "Start Processing" is Button primary
- [ ] Both drag-and-drop and file picker work
- [ ] Created runs shown below with status Badges
- [ ] File input accepts image types only

---

## Validation

1. Screenshot Upload page — verify two-column layout with dropzone
2. Drag an image over dropzone — verify indigo highlight
3. Drop image — verify thumbnail appears in grid
4. Click "Start Processing" — verify runs are created
