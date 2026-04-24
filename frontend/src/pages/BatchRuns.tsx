import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listBatches } from "../api/batch";
import type { BatchRunResponse } from "../api/types";
import { DsoBadge, DsoButton, DsoProgressBar, DsoTable } from "../components/dso";

const statusVariant: Record<string, "completed" | "processing" | "failed" | "pending" | "default"> = {
  completed: "completed",
  processing: "processing",
  partial_failure: "failed",
  failed: "failed",
  pending: "pending",
};

export default function BatchRuns() {
  const [batches, setBatches] = useState<BatchRunResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const limit = 20;

  useEffect(() => {
    load();
  }, [offset]);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await listBatches({ limit, offset });
      setBatches(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load batches");
    } finally {
      setLoading(false);
    }
  }

  const hasPrev = offset > 0;
  const hasNext = offset + limit < total;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">Batch Runs</h1>
        <Link to="/run/pipeline">
          <DsoButton>New Batch</DsoButton>
        </Link>
      </div>

      {error && (
        <DsoBadge variant="failed" className="mb-4 inline-flex">{error}</DsoBadge>
      )}

      {loading ? (
        <p className="tech-label breathing">Scanning...</p>
      ) : batches.length === 0 ? (
        <p className="text-sm text-muted">No batch runs detected.</p>
      ) : (
        <>
          <DsoTable
            columns={[
              {
                header: "Name",
                render: (b: BatchRunResponse) => b.name || <span className="text-muted">Untitled</span>,
              },
              {
                header: "Status",
                render: (b: BatchRunResponse) => (
                  <DsoBadge variant={statusVariant[b.status] ?? "default"}>
                    {b.status}
                  </DsoBadge>
                ),
              },
              {
                header: "Progress",
                render: (b: BatchRunResponse) => (
                  <div className="flex items-center gap-2">
                    <DsoProgressBar
                      value={b.completed_count}
                      max={b.total_count || 1}
                      showPercent={false}
                    />
                    <span className="text-xs text-muted tabular-nums">
                      {b.completed_count}/{b.total_count}
                    </span>
                    {b.failed_count > 0 && (
                      <span className="text-xs text-amber">({b.failed_count} failed)</span>
                    )}
                  </div>
                ),
              },
              {
                header: "Created",
                render: (b: BatchRunResponse) => (
                  <span className="text-xs text-muted">{new Date(b.created_at).toLocaleString()}</span>
                ),
              },
              {
                header: "",
                render: (b: BatchRunResponse) => (
                  <Link
                    to={`/batches/${b.id}`}
                    className="text-xs font-medium text-teal hover:text-bright transition-colors"
                  >
                    View
                  </Link>
                ),
              },
            ]}
            data={batches}
            keyFn={(b) => b.id}
          />

          <div className="mt-4 flex items-center justify-between">
            <DsoButton
              variant="secondary"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={!hasPrev}
            >
              Previous
            </DsoButton>
            <span className="tech-label">
              {offset + 1}&ndash;{Math.min(offset + limit, total)} of {total}
            </span>
            <DsoButton
              variant="secondary"
              onClick={() => setOffset(offset + limit)}
              disabled={!hasNext}
            >
              Next
            </DsoButton>
          </div>
        </>
      )}
    </div>
  );
}
