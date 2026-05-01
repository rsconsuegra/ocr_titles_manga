import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { listBatches } from "../api/batch";
import type { BatchRunResponse } from "../api/types";
import { Badge, Button, Card, EmptyState, Pagination, ProgressBar } from "../components/ui";

const LIMIT = 20;

const statusVariant: Record<string, "completed" | "processing" | "failed" | "pending" | "default"> =
  {
    completed: "completed",
    processing: "processing",
    partial_failure: "failed",
    failed: "failed",
    pending: "pending",
  };

export default function BatchRuns() {
  const navigate = useNavigate();
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
        <h1 className="font-display text-xl font-bold text-ink">Batch Runs</h1>
        <Link to="/run/pipeline">
          <Button>New Batch</Button>
        </Link>
      </div>

      {error && (
        <Badge status="failed" className="mb-4 inline-flex">
          {error}
        </Badge>
      )}

      {loading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-40 rounded-lg bg-linen animate-pulse" />
          ))}
        </div>
      ) : batches.length === 0 ? (
        <EmptyState
          title="No batch runs"
          description="Create a batch to process multiple images at once"
          actionLabel="Create Batch"
          onAction={() => navigate("/run/pipeline")}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {batches.map((b) => (
              <Card key={b.id} hover onClick={() => navigate(`/batches/${b.id}`)}>
                <h3 className="font-display text-base font-semibold text-ink mb-1">
                  {b.name || "Untitled"}
                </h3>
                <Badge status={statusVariant[b.status] ?? "default"} size="sm">
                  {b.status}
                </Badge>
                <div className="mt-3">
                  <ProgressBar value={(b.completed_count / (b.total_count || 1)) * 100} />
                </div>
                <div className="mt-2 flex items-center justify-between text-xs text-sand">
                  <span>
                    {b.completed_count}/{b.total_count} completed
                  </span>
                  {b.failed_count > 0 && (
                    <span className="text-vermillion">({b.failed_count} failed)</span>
                  )}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <span className="text-xs text-sand">
                    {new Date(b.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/batches/${b.id}`);
                    }}
                  >
                    View Details
                  </Button>
                </div>
              </Card>
            ))}
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
