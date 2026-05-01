import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  deleteProfile,
  exportProfile,
  importProfile,
  listProfiles,
  setDefaultProfile,
  validateProfileImport,
} from "../api/profiles";
import type { ProfileExportFile, ProfileImportResult, ProfileResponse } from "../api/types";
import {
  Badge,
  Button,
  EmptyState,
  ErrorBanner,
  Pagination,
  Table,
  TableSkeleton,
} from "../components/ui";

const LIMIT = 50;

export default function Profiles() {
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<ProfileExportFile | null>(null);
  const [importFileName, setImportFileName] = useState("");
  const [importValidation, setImportValidation] = useState<ProfileImportResult | null>(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  async function handleExport(id: string) {
    try {
      await exportProfile(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportFileName(file.name);
    setImportError(null);
    setImportValidation(null);
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string) as ProfileExportFile;
        if (!data.version || !data.profile || !data.profile.name) {
          setImportError("Invalid profile file: missing required fields (version, profile.name)");
          return;
        }
        setImportFile(data);
        const result = await validateProfileImport(data);
        setImportValidation(result);
      } catch (err) {
        setImportError(err instanceof Error ? err.message : "Failed to parse file");
      }
    };
    reader.readAsText(file);
  }

  async function handleConfirmImport() {
    if (!importFile) return;
    setImportLoading(true);
    setImportError(null);
    try {
      const result = await importProfile(importFile);
      if (result.errors.length > 0) {
        setImportValidation(result);
        setImportLoading(false);
        return;
      }
      setImportModalOpen(false);
      setImportFile(null);
      setImportFileName("");
      setImportValidation(null);
      load();
    } catch (e) {
      setImportError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImportLoading(false);
    }
  }

  function closeImportModal() {
    setImportModalOpen(false);
    setImportFile(null);
    setImportFileName("");
    setImportValidation(null);
    setImportError(null);
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-ink">Pipeline Profiles</h1>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setImportModalOpen(true)}>
            Import
          </Button>
          <Link to="/profiles/new">
            <Button>New Profile</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {loading ? (
        <TableSkeleton />
      ) : profiles.length === 0 ? (
        <EmptyState
          title="No profiles"
          description="Create a profile to save reusable pipeline configurations"
          actionLabel="Create Profile"
          onAction={() => navigate("/profiles/new")}
        />
      ) : (
        <>
          <Table
            columns={[
              {
                key: "name",
                header: "Name",
                render: (p: ProfileResponse) => (
                  <div>
                    <div className="font-medium text-charcoal">{p.name}</div>
                    {p.description && <div className="text-xs text-sand">{p.description}</div>}
                  </div>
                ),
              },
              {
                key: "is_default",
                header: "Default",
                render: (p: ProfileResponse) =>
                  p.is_default ? (
                    <Badge status="completed">Default</Badge>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSetDefault(p.id);
                      }}
                      className="text-xs text-sand hover:text-indigo transition-colors"
                    >
                      Set default
                    </button>
                  ),
              },
              {
                key: "enable_llm",
                header: "LLM",
                render: (p: ProfileResponse) => (
                  <span className={`text-xs ${p.enable_llm ? "text-indigo" : "text-sand"}`}>
                    <span
                      className={`size-1.5 inline-block mr-1 align-middle rounded-full ${p.enable_llm ? "bg-indigo" : "bg-sand/50"}`}
                    />
                    {p.enable_llm ? "Enabled" : "Disabled"}
                    {p.enable_llm && p.llm_provider && (
                      <span className="ml-1 text-sand">
                        ({p.llm_provider === "ollama" ? "Ollama" : "OpenRouter"})
                      </span>
                    )}
                  </span>
                ),
              },
              {
                key: "updated_at",
                header: "Updated",
                render: (p: ProfileResponse) => (
                  <span className="text-xs text-sand">
                    {new Date(p.updated_at || p.created_at).toLocaleString()}
                  </span>
                ),
              },
              {
                key: "id",
                header: "",
                render: (p: ProfileResponse) => (
                  <div className="flex items-center gap-1.5">
                    <Button
                      variant="ghost"
                      className="px-2 py-1"
                      onClick={() => handleExport(p.id)}
                      title="Export profile"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                        className="size-4"
                      >
                        <path d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z" />
                        <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
                      </svg>
                    </Button>
                    <Button
                      variant="secondary"
                      className="px-2 py-1 text-xs"
                      onClick={() => navigate(`/profiles/${p.id}/edit`)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="danger"
                      className="px-2 py-1 text-xs"
                      onClick={() => handleDelete(p.id, p.name)}
                    >
                      Delete
                    </Button>
                  </div>
                ),
              },
            ]}
            data={profiles}
          />

          {total > LIMIT && (
            <div className="mt-4">
              <Pagination
                offset={offset}
                limit={LIMIT}
                total={total}
                onPrev={() => setOffset(Math.max(0, offset - LIMIT))}
                onNext={() => setOffset(offset + LIMIT)}
              />
            </div>
          )}
        </>
      )}

      {importModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-lg border border-linen bg-snow p-6 shadow-xl">
            <h2 className="mb-4 font-display text-lg font-bold text-ink">Import Profile</h2>

            {importError && (
              <div className="mb-4">
                <ErrorBanner message={importError} />
              </div>
            )}

            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="block w-full text-sm text-sand file:mr-4 file:rounded file:border-0 file:bg-indigo-pale/50 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-indigo hover:file:bg-indigo-pale file:cursor-pointer"
              />
              {importFileName && (
                <p className="mt-2 text-xs text-sand">Selected: {importFileName}</p>
              )}
            </div>

            {importValidation && (
              <div className="mb-4 space-y-2">
                {importValidation.errors.length > 0 && (
                  <div className="rounded border border-red-500/30 bg-red-500/5 p-3">
                    <p className="mb-1 text-xs font-medium text-red-400">Errors — cannot import:</p>
                    <ul className="list-inside list-disc text-xs text-red-300">
                      {importValidation.errors.map((e, i) => (
                        <li key={i}>
                          <span className="font-mono text-red-400">{e.field}</span>: {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {importValidation.warnings.length > 0 && (
                  <div className="rounded border border-yellow-500/30 bg-yellow-500/5 p-3">
                    <p className="mb-1 text-xs font-medium text-yellow-400">Warnings:</p>
                    <ul className="list-inside list-disc text-xs text-yellow-300">
                      {importValidation.warnings.map((w, i) => (
                        <li key={i}>
                          <span className="font-mono text-yellow-400">{w.field}</span>: {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {importValidation.errors.length === 0 && (
                  <div className="rounded border border-indigo/30 bg-indigo-pale/20 p-3">
                    <p className="text-xs font-medium text-indigo">
                      Profile is valid and ready to import.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <Button variant="secondary" onClick={closeImportModal}>
                Cancel
              </Button>
              <Button
                onClick={handleConfirmImport}
                disabled={
                  !importFile ||
                  !importValidation ||
                  importValidation.errors.length > 0 ||
                  importLoading
                }
              >
                {importLoading ? "Importing..." : "Import Profile"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
