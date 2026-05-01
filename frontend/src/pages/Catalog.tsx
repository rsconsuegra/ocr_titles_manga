import { Fragment, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getCatalogExportUrl, listCatalog, updateCatalogEntry } from "../api/catalog";
import type { CatalogEntryResponse } from "../api/types";
import ConfidenceMeter from "../components/ConfidenceMeter";
import {
  Badge,
  Button,
  EmptyState,
  Input,
  Pagination,
  Select,
  TableSkeleton,
} from "../components/ui";

const STATUS_PILLS = [
  { value: "", label: "All" },
  { value: "auto_confirmed", label: "Confirmed" },
  { value: "needs_review", label: "Needs Review" },
  { value: "rejected", label: "Rejected" },
];
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
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState({ title_en: "", title_ja: "", code: "", status: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSearchDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    setLoading(true);
    listCatalog({
      status: statusFilter || undefined,
      search: searchDebounced || undefined,
      limit: LIMIT,
      offset,
    })
      .then((data) => {
        setEntries(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
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
        <h1 className="font-display text-xl font-bold text-ink">Catalog</h1>
        <Button variant="secondary" onClick={() => window.open(getCatalogExportUrl(), "_blank")}>
          Export CSV
        </Button>
      </div>

      <div className="mb-4 flex gap-3">
        <Input
          placeholder="Search title or code..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="flex-1"
        />
        <div className="flex gap-2">
          {STATUS_PILLS.map((p) => (
            <button
              key={p.value}
              onClick={() => {
                setStatusFilter(p.value);
                setOffset(0);
              }}
              className={`
                px-3 py-1.5 rounded-full text-sm font-body font-medium transition-colors
                ${
                  statusFilter === p.value
                    ? "bg-indigo-pale text-indigo"
                    : "bg-snow text-charcoal border border-linen hover:bg-cream"
                }
              `}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <TableSkeleton />
      ) : entries.length === 0 ? (
        <EmptyState
          title="No catalog entries"
          description="Run OCR on manga images to populate the catalog"
        />
      ) : (
        <>
          <div className="overflow-hidden rounded-lg border border-linen bg-snow">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-linen">
                  <th className="px-4 py-3 label-text">Title EN</th>
                  <th className="px-4 py-3 label-text">Title JA</th>
                  <th className="px-4 py-3 label-text">Code</th>
                  <th className="px-4 py-3 label-text">Confidence</th>
                  <th className="px-4 py-3 label-text">Status</th>
                  <th className="px-4 py-3 label-text">Created</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <Fragment key={entry.id}>
                    <tr
                      onClick={() => handleExpand(entry)}
                      className="cursor-pointer border-b border-linen/50 transition-colors hover:bg-indigo-pale/30"
                    >
                      <td className="px-4 py-3 text-charcoal">{entry.title_en || "\u2014"}</td>
                      <td className="px-4 py-3 text-charcoal font-japanese">
                        {entry.title_ja || "\u2014"}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-charcoal/80">
                        {entry.code || "\u2014"}
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceMeter value={entry.confidence} />
                      </td>
                      <td className="px-4 py-3">
                        <Badge status={catalogStatusVariant[entry.status] ?? "default"}>
                          {entry.status.replace("_", " ")}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-xs text-sand">
                        {new Date(entry.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {expandedId === entry.id && (
                      <tr>
                        <td colSpan={6} className="bg-cream px-4 py-3">
                          <div className="flex flex-wrap gap-3">
                            <Input
                              placeholder="Title EN"
                              value={editForm.title_en}
                              onChange={(e) =>
                                setEditForm({ ...editForm, title_en: e.target.value })
                              }
                            />
                            <Input
                              placeholder="Title JA"
                              value={editForm.title_ja}
                              onChange={(e) =>
                                setEditForm({ ...editForm, title_ja: e.target.value })
                              }
                            />
                            <Input
                              placeholder="Code / ISBN"
                              value={editForm.code}
                              onChange={(e) => setEditForm({ ...editForm, code: e.target.value })}
                            />
                            <Select
                              value={editForm.status}
                              onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}
                              options={[
                                { value: "auto_confirmed", label: "Auto Confirmed" },
                                { value: "needs_review", label: "Needs Review" },
                                { value: "rejected", label: "Rejected" },
                              ]}
                            />
                            <Button onClick={handleSave} disabled={saving}>
                              {saving ? "Saving..." : "Save"}
                            </Button>
                          </div>
                          <p className="mt-2 text-xs text-sand">
                            Source:{" "}
                            <button
                              type="button"
                              onClick={() => navigate(`/runs/${entry.source_run_id}`)}
                              className="cursor-pointer text-indigo hover:text-indigo/70 transition-colors"
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

          <div className="mt-4">
            <Pagination
              offset={offset}
              limit={LIMIT}
              total={total}
              onPrev={() => setOffset(Math.max(0, offset - LIMIT))}
              onNext={() => setOffset(offset + LIMIT)}
            />
          </div>
        </>
      )}
    </div>
  );
}
