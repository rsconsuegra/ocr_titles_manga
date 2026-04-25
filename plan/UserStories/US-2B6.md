# US-2B6: Prompt Diff Viewer

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: US-2B4 (frontend prompt list), US-2B2 (diff API endpoint)
**Blocks**: None

---

## Overview

Add a side-by-side diff viewer for comparing two prompt versions. Accessible from the prompt list (select two versions) and the prompt detail page. Uses unified diff output from the backend, rendered with syntax highlighting in the DSO dark theme.

---

## Implementation Details

### 1. `frontend/src/pages/PromptDiff.tsx`

```tsx
import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { diffPrompts, listPrompts } from "../api/client";
import type { PromptVersionResponse, PromptDiffResponse } from "../api/types";
import { DsoCard, DsoButton } from "../components/dso";

export default function PromptDiff() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const idA = searchParams.get("a");
  const idB = searchParams.get("b");

  const [prompts, setPrompts] = useState<PromptVersionResponse[]>([]);
  const [selectedA, setSelectedA] = useState(idA || "");
  const [selectedB, setSelectedB] = useState(idB || "");
  const [diff, setDiff] = useState<PromptDiffResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPrompts().then(setPrompts).catch(() => {});
  }, []);

  useEffect(() => {
    if (idA && idB) {
      loadDiff(Number(idA), Number(idB));
    }
  }, [idA, idB]);

  const loadDiff = async (a: number, b: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await diffPrompts(a, b);
      setDiff(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = () => {
    if (selectedA && selectedB && selectedA !== selectedB) {
      navigate(`/prompts/diff?a=${selectedA}&b=${selectedB}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-bright">Prompt Diff</h1>
        <DsoButton variant="ghost" onClick={() => navigate("/prompts")}>
          Back to Prompts
        </DsoButton>
      </div>

      <DsoCard variant="flat">
        <div className="flex items-end gap-4">
          <div className="flex-1">
            <label className="tech-label mb-1 block text-xs text-muted">
              Version A
            </label>
            <select
              value={selectedA}
              onChange={(e) => setSelectedA(e.target.value)}
              className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
            >
              <option value="">Select version...</option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  v{p.version_number} ({p.prompt_type})
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="tech-label mb-1 block text-xs text-muted">
              Version B
            </label>
            <select
              value={selectedB}
              onChange={(e) => setSelectedB(e.target.value)}
              className="neo-inset w-full rounded border-highlight/20 bg-inset px-3 py-2 text-sm text-bright"
            >
              <option value="">Select version...</option>
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  v{p.version_number} ({p.prompt_type})
                </option>
              ))}
            </select>
          </div>
          <DsoButton
            variant="primary"
            onClick={handleCompare}
            disabled={!selectedA || !selectedB || selectedA === selectedB}
          >
            Compare
          </DsoButton>
        </div>
      </DsoCard>

      {error && (
        <div className="neo-inset rounded-lg p-3 text-sm text-amber">{error}</div>
      )}

      {loading && (
        <p className="text-sm text-muted">Loading diff...</p>
      )}

      {diff && (
        <div className="grid grid-cols-2 gap-4">
          <DsoCard variant="lcd">
            <div className="mb-2 flex items-center gap-2">
              <span className="tech-label text-xs text-muted">
                Version A — v{diff.version_a.version_number}
              </span>
              {diff.version_a.is_active && (
                <span className="text-xs text-teal">● Active</span>
              )}
            </div>
            <pre className="overflow-auto whitespace-pre-wrap text-xs text-bright">
              {diff.version_a.content}
            </pre>
          </DsoCard>
          <DsoCard variant="lcd">
            <div className="mb-2 flex items-center gap-2">
              <span className="tech-label text-xs text-muted">
                Version B — v{diff.version_b.version_number}
              </span>
              {diff.version_b.is_active && (
                <span className="text-xs text-teal">● Active</span>
              )}
            </div>
            <pre className="overflow-auto whitespace-pre-wrap text-xs text-bright">
              {diff.version_b.content}
            </pre>
          </DsoCard>
        </div>
      )}

      {diff && diff.diff_lines.length > 0 && (
        <DsoCard variant="inset">
          <h3 className="tech-label mb-2 text-xs text-muted">Unified Diff</h3>
          <pre className="overflow-auto font-mono text-xs">
            {diff.diff_lines.map((line, i) => (
              <span
                key={i}
                className={
                  line.startsWith("+")
                    ? "text-teal"
                    : line.startsWith("-")
                      ? "text-amber"
                      : "text-muted"
                }
              >
                {line}
                {"\n"}
              </span>
            ))}
          </pre>
        </DsoCard>
      )}

      {diff && diff.diff_lines.length === 0 && (
        <DsoCard variant="flat">
          <p className="text-sm text-muted">Versions are identical.</p>
        </DsoCard>
      )}
    </div>
  );
}
```

### 2. `frontend/src/App.tsx` (addition)

```tsx
import PromptDiff from "./pages/PromptDiff";

<Route path="/prompts/diff" element={<PromptDiff />} />
```

---

## Acceptance Criteria

- [ ] `/prompts/diff?a=X&b=Y` shows side-by-side comparison of two prompt versions
- [ ] Version selector dropdowns pre-populated from URL params
- [ ] "Compare" button loads diff for selected versions
- [ ] Side-by-side view shows full content of each version in LCD panels
- [ ] Unified diff section below shows added lines (teal), removed lines (amber), unchanged (muted)
- [ ] "Versions are identical" message when no diff
- [ ] Active version indicator (teal dot) shown on each side
- [ ] "Back to Prompts" navigation link
- [ ] DSO dark theme applied

---

## Test Specifications

Manual UI testing:
- Navigate to `/prompts/diff?a=1&b=2` with seeded prompts — verify side-by-side view
- Use dropdown selectors to pick different versions — verify Compare button enables/disables
- Compare identical versions — verify "identical" message
- Verify diff lines are color-coded (teal for additions, amber for removals)
