import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { deleteProfile, listProfiles, setDefaultProfile } from "../api/profiles";
import type { ProfileResponse } from "../api/types";
import { DsoBadge, DsoButton, DsoErrorBanner, DsoPagination, DsoTable } from "../components/dso";

const LIMIT = 50;

export default function Profiles() {
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listProfiles(LIMIT, offset);
      setProfiles(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load profiles");
    } finally {
      setLoading(false);
    }
  }, [offset]);

  /* eslint-disable react-hooks/set-state-in-effect -- data-fetching effect */
  useEffect(() => {
    load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete profile "${name}"?`)) return;
    try {
      await deleteProfile(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function handleSetDefault(id: string) {
    try {
      await setDefaultProfile(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to set default");
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">Pipeline Profiles</h1>
        <Link to="/profiles/new">
          <DsoButton>New Profile</DsoButton>
        </Link>
      </div>

      {error && <DsoErrorBanner className="mb-4">{error}</DsoErrorBanner>}

      {loading ? (
        <p className="tech-label breathing">Scanning...</p>
      ) : profiles.length === 0 ? (
        <p className="text-sm text-muted">No profiles detected. Create one to save reusable pipeline configurations.</p>
      ) : (
        <>
          <DsoTable
            columns={[
              {
                header: "Name",
                render: (p: ProfileResponse) => (
                  <div>
                    <div className="font-medium text-bright">{p.name}</div>
                    {p.description && <div className="text-xs text-muted">{p.description}</div>}
                  </div>
                ),
              },
              {
                header: "Default",
                render: (p: ProfileResponse) =>
                  p.is_default ? (
                    <DsoBadge variant="completed">Default</DsoBadge>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleSetDefault(p.id); }}
                      className="text-xs text-muted hover:text-teal transition-colors"
                    >
                      Set default
                    </button>
                  ),
              },
              {
                header: "LLM",
                render: (p: ProfileResponse) => (
                  <span className={`text-xs ${p.enable_llm ? "text-teal" : "text-muted"}`}>
                    <span className={`led ${p.enable_llm ? "led-active" : "led-off"} size-1.5 inline-block mr-1 align-middle`} />
                    {p.enable_llm ? "Enabled" : "Disabled"}
                    {p.enable_llm && p.llm_provider && (
                      <span className="ml-1 text-muted">({p.llm_provider === "ollama" ? "Ollama" : "OpenRouter"})</span>
                    )}
                  </span>
                ),
              },
              {
                header: "Updated",
                render: (p: ProfileResponse) => (
                  <span className="text-xs text-muted">{new Date(p.updated_at || p.created_at).toLocaleString()}</span>
                ),
              },
              {
                header: "",
                render: (p: ProfileResponse) => (
                  <>
                    <button
                      onClick={() => navigate(`/profiles/${p.id}/edit`)}
                      className="text-xs font-medium text-teal hover:text-bright transition-colors"
                    >
                      Edit
                    </button>
                    <DsoButton
                      variant="danger"
                      className="px-2 py-0.5 text-xs"
                      onClick={() => handleDelete(p.id, p.name)}
                    >
                      Delete
                    </DsoButton>
                  </>
                ),
              },
            ]}
            data={profiles}
            keyFn={(p) => p.id}
          />

          {total > LIMIT && (
            <DsoPagination
              page={Math.floor(offset / LIMIT) + 1}
              totalPages={Math.ceil(total / LIMIT)}
              totalItems={total}
              pageSize={LIMIT}
              onPageChange={(p) => setOffset((p - 1) * LIMIT)}
              className="mt-4"
            />
          )}
        </>
      )}
    </div>
  );
}
