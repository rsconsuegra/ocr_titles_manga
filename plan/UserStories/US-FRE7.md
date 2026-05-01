# US-FRE7: Redesigned Profile Editor

**Sub-phase**: FR-E — Secondary Pages
**Depends on**: US-FRC7 (DSO removed, new components), US-FRE6 (profiles page)
**Blocks**: None

---

## Story

> As a user, I want a multi-section profile editor with clear save/cancel actions so that I can create or modify pipeline configurations.

---

## Scope

### In Scope
- Rewrite ProfileEditor.tsx with stacked Card sections
- Name/Description, Preprocessing, OCR, LLM sections
- TopBar Save/Cancel buttons
- Edit mode loads existing profile from API

### Out of Scope
- New configuration options
- Profile validation UI

---

## Implementation Details

### 1. `frontend/src/pages/ProfileEditor.tsx` (rewritten)

Layout:
```
┌─────────────────────────────────────────────────┐
│ TopBar: [New Profile]         [Save] [Cancel]   │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ Profile Details                              │ │
│ │ Name:        [________________]              │ │
│ │ Description: [________________]              │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ Preprocessing                                │ │
│ │ [PreprocessStepCard instances...]            │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ OCR Models                                   │ │
│ │ [OcrModelCard instances...]                  │ │
│ └─────────────────────────────────────────────┘ │
│                                                  │
│ ┌─────────────────────────────────────────────┐ │
│ │ LLM Settings                                 │ │
│ │ [LlmConfigSection]                           │ │
│ │ [PromptSettingsPanel]                        │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**TopBar actions:** "Save" Button primary + "Cancel" Button ghost

**Stacked Card sections:**
- Profile Details: Input for name, Input for description
- Preprocessing: PreprocessStepCard instances for each step
- OCR Models: OcrModelCard instances for each model
- LLM Settings: LlmConfigSection + PromptSettingsPanel

**Edit mode:** On mount, if route is `/profiles/:id/edit`, load profile from `getProfile(id)` API and populate all sections

**Save logic:** Calls `createProfile` or `updateProfile` based on mode (new vs edit)

**Validation errors:** Inline on Input components via `error` prop

---

## Acceptance Criteria

- [ ] Stacked Card sections: Name/Description, Preprocessing, OCR, LLM
- [ ] Name section uses Input component
- [ ] Preprocessing section uses PreprocessStepCard instances
- [ ] OCR section uses OcrModelCard instances
- [ ] LLM section uses LlmConfigSection + PromptSettingsPanel
- [ ] TopBar shows "Save" Button primary and "Cancel" Button ghost
- [ ] Edit mode loads existing profile data from API on mount
- [ ] Save calls create or update API endpoint based on mode
- [ ] Validation errors shown inline on Input components
- [ ] Cancel navigates back to `/profiles`

---

## Validation

1. Screenshot Profile Editor (new mode) — verify empty form with all sections
2. Navigate to edit mode — verify form populated with profile data
3. Fill name + click Save — verify API call and navigation back
4. Submit with empty name — verify validation error
