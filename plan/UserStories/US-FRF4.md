# US-FRF4: Consistent Hover and Focus States

**Sub-phase**: FR-F — Polish
**Depends on**: US-FRC1–C6 (components defined), US-FRB1 (sidebar), all page stories
**Blocks**: US-FRF5 (final cleanup)

---

## Story

> As a user, I want all interactive elements to provide clear visual feedback on hover and focus so that I can tell what is clickable and where my keyboard focus is.

---

## Scope

### In Scope
- Audit all interactive elements for hover feedback
- Ensure all buttons, inputs, table rows, nav items have hover states
- Ensure all interactive elements have keyboard-accessible focus states (focus-visible)

### Out of Scope
- New interactive elements
- Touch/mobile interactions (desktop only)

---

## Implementation Details

### Hover state checklist

| Element | Hover State | Implementation |
|---------|-------------|----------------|
| Button primary | bg-indigo-light | Already in Button component |
| Button secondary | bg-cream | Already in Button component |
| Button danger | opacity-90 | Already in Button component |
| Button ghost | bg-cream | Already in Button component |
| Card (hover=true) | shadow-md | Already in Card component |
| Table rows (clickable) | bg-cream/50 | Already in Table component |
| Sidebar nav items | bg-cream text-ink | Already in Sidebar component |
| Filter pills (inactive) | bg-cream | Already in filter implementations |
| Input | border-indigo/50 | Add to Input hover |
| Select | border-indigo/50 | Add to Select hover |

### Focus state checklist

| Element | Focus State | Implementation |
|---------|-------------|----------------|
| All buttons | ring-2 ring-indigo/20 ring-offset-2 | Already in Button (focus-visible) |
| Input | border-indigo ring-2 ring-indigo/20 | Already in Input |
| Select | border-indigo ring-2 ring-indigo/20 | Already in Select |
| Sidebar nav items | outline-none + visible ring | Add to Sidebar |
| Table rows (clickable) | outline-none + visible ring | Add to Table |
| Filter pills | outline-none + visible ring | Add to filter implementations |

### Active/pressed state

All buttons: `active:scale-[0.98]` — already in Button component.

### Implementation additions

**Input hover:**
```tsx
// Add to Input className:
"hover:border-indigo/50"
```

**Sidebar nav focus:**
```tsx
// Add to NavLink className:
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo/20 focus-visible:ring-offset-1"
```

**Table row focus (keyboard navigation):**
```tsx
// Add to <tr> when onRowClick provided:
"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo/20"
// Add tabIndex={0} and onKeyDown for Enter/Space
```

---

## Acceptance Criteria

- [ ] All buttons show visible hover state (bg change)
- [ ] All buttons show focus-visible ring (2px indigo, 2px offset)
- [ ] All inputs and selects show indigo focus ring on focus
- [ ] All table rows with onRowClick show hover:bg-cream/50
- [ ] All sidebar nav items show hover:bg-cream
- [ ] Focus states use `focus-visible` (not `focus`) for keyboard accessibility
- [ ] Active/pressed state for buttons: scale-[0.98]
- [ ] No outline artifacts on click (only focus-visible triggers ring)
- [ ] Tab navigation works through all interactive elements

---

## Validation

1. Tab through the entire page — verify focus ring appears on each interactive element
2. Hover over each interactive element — verify visible hover state
3. Click buttons — verify no outline artifact, only subtle scale
4. Use keyboard to navigate table — verify focus indicators
