# US-2B5: Frontend Prompt Editor with Agenta Push

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: US-2B4 (frontend prompt list), US-2B2 (Prompt CRUD API)
**Blocks**: None

---

## Overview

Create a prompt editor page for creating new prompt versions and editing existing ones. The editor includes a textarea for prompt content, metadata fields (type, tags), an option to activate on save, and a "Push to Agenta" toggle. For existing prompts, shows version history context and diff link.

---

## Implementation Details

### 1. `frontend/src/pages/PromptEditor.tsx`

```tsx
import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getPrompt,
  createPrompt,
  updatePrompt,
  activatePrompt,
} from "../api/client";
import type { PromptVersionResponse } from "../api/types";
import { DsoCard, DsoButton, DsoInput } from "../components/dso";

export default function PromptEditor() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [existing, setExisting] = useState<PromptVersionResponse | null>(null);
  const [promptType, setPromptType] = useState("llm");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [activate, setActivate] = useState(false);
  const [pushToAgenta, setPushToAgenta] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (id) {
      getPrompt(Number(id))
        .then((p) => {
          setExisting(p);
          setPromptType(p.prompt_type);
          setContent(p.content);
          setTags(p.tags.join(", "));
        })
        .catch((e) => setError(e.message));
    }
  }, [id]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const tagList = tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);

      if (isEdit && existing) {
        await updatePrompt(existing.id, { content, tags: tagList });
        if (activate) await activatePrompt(existing.id);
      } else {
        const result = await createPrompt({
          prompt_type: promptType,
          content,
          tags: tagList,
          activate,
          push_to_agenta: pushToAgenta,
        });
        navigate(`/prompts/${result.id}`);
        return;
      }
      navigate("/prompts");
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold text-bright">
        {isEdit ? `Edit Prompt v${existing?.version_number}` : "New Prompt Version"}
      </h1>

      {error && (
        <div className="neo-inset rounded-lg p-3 text-sm text-amber">{error}</div>
      )}

      {!isEdit && (
        <DsoCard variant="flat">
          <label className="tech-label mb-1 block text-xs text-muted">Prompt Type</label>
          <select
            value={promptType}
            onChange={(e) => setPromptType(e.target.value)}
            className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
          >
            <option value="llm">LLM Extraction</option>
          </select>
        </DsoCard>
      )}

      <DsoCard variant="flat">
        <label className="tech-label mb-1 block text-xs text-muted">
          Prompt Content
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={20}
          className="neo-deep-inset w-full resize-y rounded border-highlight/10 bg-inset p-4 font-mono text-sm text-bright"
          placeholder="Enter prompt content..."
        />
        <div className="mt-1 text-right text-xs text-muted">
          {content.length} characters
        </div>
      </DsoCard>

      <DsoCard variant="flat">
        <label className="tech-label mb-1 block text-xs text-muted">Tags</label>
        <input
          type="text"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="Comma-separated tags"
          className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
        />
      </DsoCard>

      <DsoCard variant="flat">
        <div className="flex items-center gap-6">
          <label className="flex items-center gap-2 text-sm text-bright">
            <input
              type="checkbox"
              checked={activate}
              onChange={(e) => setActivate(e.target.checked)}
              className="accent-teal"
            />
            Activate this version
          </label>
          {!isEdit && (
            <label className="flex items-center gap-2 text-sm text-bright">
              <input
                type="checkbox"
                checked={pushToAgenta}
                onChange={(e) => setPushToAgenta(e.target.checked)}
                className="accent-teal"
              />
              Push to Agenta
            </label>
          )}
        </div>
      </DsoCard>

      <div className="flex gap-3">
        <DsoButton variant="primary" onClick={handleSave} disabled={saving || !content}>
          {saving ? "Saving..." : isEdit ? "Update Prompt" : "Create Prompt"}
        </DsoButton>
        <DsoButton variant="ghost" onClick={() => navigate("/prompts")}>
          Cancel
        </DsoButton>
      </div>
    </div>
  );
}
```

### 2. `frontend/src/App.tsx` (addition)

```tsx
import PromptEditor from "./pages/PromptEditor";

<Route path="/prompts/new" element={<PromptEditor />} />
<Route path="/prompts/:id/edit" element={<PromptEditor />} />
```

---

## Acceptance Criteria

- [ ] `/prompts/new` shows empty editor with type selector, content textarea, tags input
- [ ] `/prompts/:id/edit` loads existing prompt data into editor
- [ ] "Create Prompt" POSTs to API with type, content, tags, activate flag
- [ ] "Update Prompt" PATCHes existing prompt content/tags
- [ ] "Activate this version" checkbox triggers activate API call after save
- [ ] "Push to Agenta" checkbox only shown on create (not edit)
- [ ] Character count displayed below textarea
- [ ] Save disabled when content is empty
- [ ] Cancel navigates back to `/prompts`
- [ ] Error messages displayed in amber-tinted panel
- [ ] DSO dark theme applied

---

## Test Specifications

Manual UI testing:
- Create new prompt: fill form, save, verify redirect to detail page
- Edit existing prompt: change content, save, verify update on list page
- Activate on save: check box, save, verify prompt shows "Active" badge
- Empty content: verify save button disabled
- Cancel: verify navigation back to prompts list
