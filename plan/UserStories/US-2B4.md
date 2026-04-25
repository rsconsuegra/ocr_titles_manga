# US-2B4: Frontend Prompt Management — List & Browse

**Sub-phase**: 2B — Agenta.ai Integration
**Depends on**: US-2B2 (Prompt CRUD API), US-2B3 (prompt version tracking)
**Blocks**: US-2B5 (prompt editor), US-2B6 (diff viewer)

---

## Overview

Create the frontend pages and API layer for browsing prompt versions. Includes a prompt list page with filtering by type, version badges showing active/synced status, and a read-only detail view. Navigation entry added to the app shell.

---

## Implementation Details

### 1. `frontend/src/api/types.ts` (additions)

```typescript
export interface PromptVersionResponse {
  id: number;
  prompt_type: string;
  content: string;
  version_number: number;
  agenta_id: string | null;
  is_active: boolean;
  tags: string[];
  source: string | null;
  last_synced_at: string | null;
  created_at: string;
}

export interface PromptVersionCreateRequest {
  prompt_type: string;
  content: string;
  tags?: string[];
  activate?: boolean;
  push_to_agenta?: boolean;
}

export interface PromptVersionUpdateRequest {
  content?: string;
  tags?: string[];
  is_active?: boolean;
}

export interface PromptDiffResponse {
  version_a: PromptVersionResponse;
  version_b: PromptVersionResponse;
  diff_lines: string[];
}

export interface PromptSyncResponse {
  pulled: number;
  pushed: number;
  conflicts: number;
  errors: string[];
}
```

### 2. `frontend/src/api/prompts.ts`

```typescript
import { apiFetch } from "./pipeline";
import type {
  PromptVersionResponse,
  PromptVersionCreateRequest,
  PromptVersionUpdateRequest,
  PromptDiffResponse,
  PromptSyncResponse,
} from "./types";

export function listPrompts(promptType?: string) {
  const params = promptType ? `?prompt_type=${promptType}` : "";
  return apiFetch<PromptVersionResponse[]>(`/api/v1/prompts${params}`);
}

export function getPrompt(id: number) {
  return apiFetch<PromptVersionResponse>(`/api/v1/prompts/${id}`);
}

export function createPrompt(data: PromptVersionCreateRequest) {
  return apiFetch<PromptVersionResponse>("/api/v1/prompts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function updatePrompt(id: number, data: PromptVersionUpdateRequest) {
  return apiFetch<PromptVersionResponse>(`/api/v1/prompts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export function activatePrompt(id: number) {
  return apiFetch<PromptVersionResponse>(`/api/v1/prompts/${id}/activate`, {
    method: "POST",
  });
}

export function deletePrompt(id: number) {
  return apiFetch<void>(`/api/v1/prompts/${id}`, { method: "DELETE" });
}

export function diffPrompts(idA: number, idB: number) {
  return apiFetch<PromptDiffResponse>(
    `/api/v1/prompts/diff/${idA}/${idB}`
  );
}

export function syncWithAgenta() {
  return apiFetch<PromptSyncResponse>("/api/v1/prompts/sync", {
    method: "POST",
  });
}
```

### 3. `frontend/src/api/client.ts` (addition)

```typescript
export * from "./prompts";
```

### 4. `frontend/src/pages/Prompts.tsx`

```tsx
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { listPrompts, syncWithAgenta } from "../api/client";
import type { PromptVersionResponse, PromptSyncResponse } from "../api/types";
import { DsoCard, DsoBadge, DsoButton, DsoPagination } from "../components/dso";

export default function Prompts() {
  const [prompts, setPrompts] = useState<PromptVersionResponse[]>([]);
  const [promptType, setPromptType] = useState<string>("");
  const [syncResult, setSyncResult] = useState<PromptSyncResponse | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const perPage = 20;

  useEffect(() => {
    listPrompts(promptType || undefined)
      .then(setPrompts)
      .catch((e) => setError(e.message));
  }, [promptType]);

  const handleSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await syncWithAgenta();
      setSyncResult(result);
      const updated = await listPrompts(promptType || undefined);
      setPrompts(updated);
    } catch (e: any) {
      setError(e.message || "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const paged = prompts.slice(page * perPage, (page + 1) * perPage);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-bright">Prompt Versions</h1>
        <div className="flex gap-3">
          <Link to="/prompts/new">
            <DsoButton variant="primary">New Prompt</DsoButton>
          </Link>
          <DsoButton variant="secondary" onClick={handleSync} disabled={syncing}>
            {syncing ? "Syncing..." : "Sync with Agenta"}
          </DsoButton>
        </div>
      </div>

      {syncResult && (
        <DsoCard variant="flat">
          <p className="text-sm text-bright">
            Sync complete: {syncResult.pulled} pulled, {syncResult.pushed} pushed
            {syncResult.conflicts > 0 && `, ${syncResult.conflicts} conflicts`}
          </p>
          {syncResult.errors.length > 0 && (
            <ul className="mt-2 text-xs text-amber">
              {syncResult.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          )}
        </DsoCard>
      )}

      {error && (
        <div className="neo-inset rounded-lg p-3 text-sm text-amber">{error}</div>
      )}

      <div className="flex items-center gap-3">
        <label className="tech-label text-xs text-muted">Filter by type</label>
        <select
          value={promptType}
          onChange={(e) => { setPromptType(e.target.value); setPage(0); }}
          className="neo-inset rounded border-highlight/20 bg-inset px-3 py-1.5 text-sm text-bright"
        >
          <option value="">All types</option>
          <option value="llm">LLM</option>
        </select>
      </div>

      <DsoCard variant="inset">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-highlight/10">
              <th className="px-3 py-2 tech-label text-muted">Version</th>
              <th className="px-3 py-2 tech-label text-muted">Type</th>
              <th className="px-3 py-2 tech-label text-muted">Preview</th>
              <th className="px-3 py-2 tech-label text-muted">Status</th>
              <th className="px-3 py-2 tech-label text-muted">Source</th>
              <th className="px-3 py-2 tech-label text-muted">Created</th>
              <th className="px-3 py-2 tech-label text-muted">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((p) => (
              <tr
                key={p.id}
                className="border-b border-highlight/5 transition-colors hover:bg-highlight/5"
              >
                <td className="px-3 py-2 font-mono text-bright">v{p.version_number}</td>
                <td className="px-3 py-2 text-bright">{p.prompt_type}</td>
                <td className="max-w-xs truncate px-3 py-2 text-muted">
                  {p.content.substring(0, 80)}...
                </td>
                <td className="px-3 py-2">
                  {p.is_active && <DsoBadge status="completed">Active</DsoBadge>}
                  {!p.is_active && <DsoBadge status="default">Inactive</DsoBadge>}
                </td>
                <td className="px-3 py-2 text-muted">{p.source || "local"}</td>
                <td className="px-3 py-2 text-muted">
                  {new Date(p.created_at).toLocaleDateString()}
                </td>
                <td className="px-3 py-2">
                  <Link to={`/prompts/${p.id}`} className="text-teal hover:underline">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </DsoCard>

      {prompts.length > perPage && (
        <DsoPagination
          page={page}
          total={prompts.length}
          perPage={perPage}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
```

### 5. `frontend/src/pages/PromptDetail.tsx`

Read-only detail view showing full prompt content, metadata, sync status, and action buttons (edit, activate, delete, diff).

### 6. `frontend/src/App.tsx` (addition)

Add route and nav entry:

```tsx
import Prompts from "./pages/Prompts";
import PromptDetail from "./pages/PromptDetail";

// In routes:
<Route path="/prompts" element={<Prompts />} />
<Route path="/prompts/:id" element={<PromptDetail />} />

// In navigation "Config" dropdown:
<Link to="/prompts">Prompt Versions</Link>
```

---

## Acceptance Criteria

- [ ] `/prompts` page lists all prompt versions in a dark-themed table
- [ ] Filter by prompt type works (All / LLM)
- [ ] Each row shows version number, type, content preview, active badge, source, date
- [ ] "Sync with Agenta" button triggers sync and shows result summary
- [ ] Clicking a row navigates to `/prompts/:id` detail view
- [ ] Detail view shows full prompt content, metadata, sync status
- [ ] "New Prompt" button navigates to editor page
- [ ] Navigation includes "Prompt Versions" link in Config dropdown
- [ ] DSO dark theme applied (neo-panel, neo-inset, tech-label, etc.)

---

## Test Specifications

Manual UI testing (no frontend test framework in project):
- Navigate to `/prompts` and verify table renders with prompt data from API
- Test type filter dropdown changes displayed prompts
- Click "Sync with Agenta" with no Agenta configured — verify 503 error displayed
- Click a prompt row — verify navigation to detail page with full content
