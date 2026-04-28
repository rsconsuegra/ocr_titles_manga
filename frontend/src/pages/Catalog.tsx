import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getCatalogExportUrl, listCatalog, updateCatalogEntry } from "../api/catalog";
import type { CatalogEntryResponse } from "../api/types";
import ConfidenceMeter from "../components/ConfidenceMeter";
import { DsoBadge, DsoButton, DsoInput, DsoPagination, DsoSelect } from "../components/dso";

const STATUSES = ["", "auto_confirmed", "needs_review", "rejected"];
const LIMIT = 20;

const catalogStatusVariant: Record<string, "completed" | "review" | "failed" | "default"> = {
  auto_confirmed: "completed",
  needs_review: "review",
  rejected: "failed",
};

export default function Catalog() {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<CatalogEntryResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [searchDebounced, setSearchDebounced] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title_en: "", title_ja: "", code: "", status: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    listCatalog({
      status: statusFilter || undefined,
      search: searchDebounced || undefined,
      limit: LIMIT,
      offset,
    }).then((data) => {
      setEntries(data.items);
      setTotal(data.total);
    });
  }, [statusFilter, searchDebounced, offset]);

  async function handleSave() {
    if (!expandedId) return;
    setSaving(true);
    await updateCatalogEntry(expandedId, editForm);
    setSaving(false);
    setExpandedId(null);
    const data = await listCatalog({
      status: statusFilter || undefined,
      search: searchDebounced || undefined,
      limit: LIMIT,
      offset,
    });
    setEntries(data.items);
    setTotal(data.total);
  }

  function handleExpand(entry: CatalogEntryResponse) {
    if (expandedId === entry.id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(entry.id);
    setEditForm({
      title_en: entry.title_en || "",
      title_ja: entry.title_ja || "",
      code: entry.code || "",
      status: entry.status,
    });
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">Catalog</h1>
        <DsoButton
          variant="secondary"
          onClick={() => window.open(getCatalogExportUrl(), "_blank")}
        >
          Export CSV
        </DsoButton>
      </div>

      <div className="mb-4 flex gap-3">
        <DsoInput
          placeholder="Search title or code..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="flex-1"
        />
        <DsoSelect
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setOffset(0);
          }}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? s.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "All Statuses"}
            </option>
          ))}
        </DsoSelect>
      </div>

      {entries.length === 0 ? (
        <p className="text-sm text-muted">
          No catalog entries detected. Upload images and run the pipeline to populate.
        </p>
      ) : (
        <>
          <div className="neo-inset overflow-hidden rounded-lg">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-highlight/20">
                  <th className="px-4 py-3 tech-label text-muted">Title EN</th>
                  <th className="px-4 py-3 tech-label text-muted">Title JA</th>
                  <th className="px-4 py-3 tech-label text-muted">Code</th>
                  <th className="px-4 py-3 tech-label text-muted">Confidence</th>
                  <th className="px-4 py-3 tech-label text-muted">Status</th>
                  <th className="px-4 py-3 tech-label text-muted">Created</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <Fragment key={entry.id}>
                    <tr
                      onClick={() => handleExpand(entry)}
                      className="cursor-pointer border-b border-highlight/10 transition-colors hover:bg-teal/5"
                    >
                      <td className="px-4 py-3 text-bright/90">{entry.title_en || "—"}</td>
                      <td className="px-4 py-3 text-bright/90">{entry.title_ja || "—"}</td>
                      <td className="px-4 py-3 font-mono text-xs text-bright/80">{entry.code || "—"}</td>
                      <td className="px-4 py-3"><ConfidenceMeter value={entry.confidence} /></td>
                      <td className="px-4 py-3">
                        <DsoBadge variant={catalogStatusVariant[entry.status] ?? "default"}>
                          {entry.status.replace("_", " ")}
                        </DsoBadge>
                      </td>
                      <td className="px-4 py-3 text-xs text-muted">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {expandedId === entry.id && (
                      <tr>
                        <td colSpan={6} className="neo-deep-inset px-4 py-3">
                          <div className="flex flex-wrap gap-3">
                            <DsoInput
                              placeholder="Title EN"
                              value={editForm.title_en}
                              onChange={(e) => setEditForm({ ...editForm, title_en: e.target.value })}
                            />
                            <DsoInput
                              placeholder="Title JA"
                              value={editForm.title_ja}
                              onChange={(e) => setEditForm({ ...editForm, title_ja: e.target.value })}
                            />
                            <DsoInput
                              placeholder="Code / ISBN"
                              value={editForm.code}
                              onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                            />
                            <DsoSelect
                              value={editForm.status}
                              onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                            >
                              <option value="auto_confirmed">Auto Confirmed</option>
                              <option value="needs_review">Needs Review</option>
                              <option value="rejected">Rejected</option>
                            </DsoSelect>
                            <DsoButton onClick={handleSave} disabled={saving}>
                              {saving ? "Saving..." : "Save"}
                            </DsoButton>
                          </div>
                          <p className="mt-2 text-xs text-muted">
                            Source:{" "}
                            <button
                              type="button"
                              onClick={() => navigate(`/runs/${entry.source_run_id}`)}
                              className="cursor-pointer text-teal hover:text-bright transition-colors"
                            >
                              Run #{entry.source_run_id.slice(0, 8)}
                            </button>
                          </p>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <DsoPagination
            page={Math.floor(offset / LIMIT) + 1}
            totalPages={Math.ceil(total / LIMIT)}
            totalItems={total}
            pageSize={LIMIT}
            onPageChange={(p) => setOffset((p - 1) * LIMIT)}
            className="mt-4"
          />
        </>
      )}
    </div>
  );
}
