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
import type {
  ProfileExportFile,
  ProfileImportResult,
  ProfileResponse,
} from "../api/types";
import {
  DsoBadge,
  DsoButton,
  DsoErrorBanner,
  DsoPagination,
  DsoTable,
} from "../components/dso";

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
  const [importValidation, setImportValidation] =
    useState<ProfileImportResult | null>(null);
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
        setImportError(
          err instanceof Error ? err.message : "Failed to parse file",
        );
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
        <h1 className="font-display text-xl font-bold text-bright">
          Pipeline Profiles
        </h1>
        <div className="flex items-center gap-2">
          <DsoButton variant="secondary" onClick={() => setImportModalOpen(true)}>
            Import
          </DsoButton>
          <Link to="/profiles/new">
            <DsoButton>New Profile</DsoButton>
          </Link>
        </div>
      </div>

      {error && <DsoErrorBanner className="mb-4">{error}</DsoErrorBanner>}

      {loading ? (
        <p className="tech-label breathing">Scanning...</p>
      ) : profiles.length === 0 ? (
        <p className="text-sm text-muted">
          No profiles detected. Create one to save reusable pipeline
          configurations.
        </p>
      ) : (
        <>
          <DsoTable
            columns={[
              {
                header: "Name",
                render: (p: ProfileResponse) => (
                  <div>
                    <div className="font-medium text-bright">{p.name}</div>
                    {p.description && (
                      <div className="text-xs text-muted">{p.description}</div>
                    )}
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
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSetDefault(p.id);
                      }}
                      className="text-xs text-muted hover:text-teal transition-colors"
                    >
                      Set default
                    </button>
                  ),
              },
              {
                header: "LLM",
                render: (p: ProfileResponse) => (
                  <span
                    className={`text-xs ${p.enable_llm ? "text-teal" : "text-muted"}`}
                  >
                    <span
                      className={`led ${p.enable_llm ? "led-active" : "led-off"} size-1.5 inline-block mr-1 align-middle`}
                    />
                    {p.enable_llm ? "Enabled" : "Disabled"}
                    {p.enable_llm && p.llm_provider && (
                      <span className="ml-1 text-muted">
                        (
                        {p.llm_provider === "ollama"
                          ? "Ollama"
                          : "OpenRouter"}
                        )
                      </span>
                    )}
                  </span>
                ),
              },
              {
                header: "Updated",
                render: (p: ProfileResponse) => (
                  <span className="text-xs text-muted">
                    {new Date(p.updated_at || p.created_at).toLocaleString()}
                  </span>
                ),
              },
              {
                header: "",
                render: (p: ProfileResponse) => (
                  <div className="flex items-center gap-1.5">
                    <DsoButton
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
                    </DsoButton>
                    <DsoButton
                      variant="secondary"
                      className="px-2 py-1 text-xs"
                      onClick={() => navigate(`/profiles/${p.id}/edit`)}
                    >
                      Edit
                    </DsoButton>
                    <DsoButton
                      variant="danger"
                      className="px-2 py-1 text-xs"
                      onClick={() => handleDelete(p.id, p.name)}
                    >
                      Delete
                    </DsoButton>
                  </div>
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

      {importModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-lg border border-highlight/20 bg-panel p-6 shadow-xl">
            <h2 className="mb-4 font-display text-lg font-bold text-bright">
              Import Profile
            </h2>

            {importError && (
              <DsoErrorBanner className="mb-4">{importError}</DsoErrorBanner>
            )}

            <div className="mb-4">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                onChange={handleFileSelect}
                className="block w-full text-sm text-muted file:mr-4 file:rounded file:border-0 file:bg-teal/20 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-teal hover:file:bg-teal/30 file:cursor-pointer"
              />
              {importFileName && (
                <p className="mt-2 text-xs text-muted">
                  Selected: {importFileName}
                </p>
              )}
            </div>

            {importValidation && (
              <div className="mb-4 space-y-2">
                {importValidation.errors.length > 0 && (
                  <div className="rounded border border-red-500/30 bg-red-500/5 p-3">
                    <p className="mb-1 text-xs font-medium text-red-400">
                      Errors — cannot import:
                    </p>
                    <ul className="list-inside list-disc text-xs text-red-300">
                      {importValidation.errors.map((e, i) => (
                        <li key={i}>
                          <span className="font-mono text-red-400">
                            {e.field}
                          </span>
                          : {e.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {importValidation.warnings.length > 0 && (
                  <div className="rounded border border-yellow-500/30 bg-yellow-500/5 p-3">
                    <p className="mb-1 text-xs font-medium text-yellow-400">
                      Warnings:
                    </p>
                    <ul className="list-inside list-disc text-xs text-yellow-300">
                      {importValidation.warnings.map((w, i) => (
                        <li key={i}>
                          <span className="font-mono text-yellow-400">
                            {w.field}
                          </span>
                          : {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {importValidation.errors.length === 0 && (
                  <div className="rounded border border-teal/30 bg-teal/5 p-3">
                    <p className="text-xs font-medium text-teal">
                      Profile is valid and ready to import.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="flex items-center justify-end gap-3">
              <DsoButton variant="secondary" onClick={closeImportModal}>
                Cancel
              </DsoButton>
              <DsoButton
                onClick={handleConfirmImport}
                disabled={
                  !importFile ||
                  !importValidation ||
                  importValidation.errors.length > 0 ||
                  importLoading
                }
              >
                {importLoading ? "Importing..." : "Import Profile"}
              </DsoButton>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
