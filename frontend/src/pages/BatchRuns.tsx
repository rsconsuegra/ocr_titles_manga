import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listBatches } from "../api/batch";
import type { BatchRunResponse } from "../api/types";
import { DsoBadge, DsoButton, DsoPagination, DsoProgressBar, DsoTable } from "../components/dso";

const LIMIT = 20;

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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listBatches({ limit: LIMIT, offset });
      setBatches(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load batches");
    } finally {
      setLoading(false);
    }
  }, [offset]);

  /* eslint-disable react-hooks/set-state-in-effect -- data-fetching effect */
  useEffect(() => {
    load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

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
