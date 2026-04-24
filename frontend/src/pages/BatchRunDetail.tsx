import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getBatchDetail, triggerBatch } from "../api/batch";
import { triggerPipeline } from "../api/pipeline";
import type { BatchRunDetailResponse } from "../api/types";
import { DsoButton, DsoCard, DsoErrorBanner, DsoProgressBar, DsoTable } from "../components/dso";
import RunStatusBadge from "../components/RunStatusBadge";

export default function BatchRunDetail() {
  const { id } = useParams<{ id: string }>();
  const [batch, setBatch] = useState<BatchRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  useEffect(() => {
    if (id) load();
  }, [id]);

  useEffect(() => {
    if (!batch || !["processing"].includes(batch.status)) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [batch?.status]);

  async function load() {
    if (!id) return;
    try {
      const data = await getBatchDetail(id);
      setBatch(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load batch");
    } finally {
      setLoading(false);
    }
  }

  async function handleTrigger() {
    if (!id) return;
    setTriggering(true);
    setError(null);
    try {
      const updated = await triggerBatch(id);
      setBatch((prev) => (prev ? { ...prev, ...updated } : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trigger failed");
    } finally {
      setTriggering(false);
    }
  }

  async function handleRetryRun(runId: string) {
    setRetryingId(runId);
    setError(null);
    try {
      await triggerPipeline(runId);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetryingId(null);
    }
  }

  if (loading) return <p className="tech-label breathing">Loading...</p>;
  if (!batch) return <DsoErrorBanner>Batch not found</DsoErrorBanner>;

  const finished = batch.completed_count + batch.failed_count;
  const pct = batch.total_count > 0 ? Math.round((finished / batch.total_count) * 100) : 0;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <Link to="/batches" className="text-sm text-teal hover:text-bright transition-colors">
            &larr; All Batches
          </Link>
          <h1 className="mt-1 font-display text-xl font-bold text-bright">
            {batch.name || "Untitled Batch"}
          </h1>
        </div>
        {batch.status === "pending" && (
          <DsoButton onClick={handleTrigger} disabled={triggering}>
            {triggering ? "Triggering..." : "Process All"}
          </DsoButton>
        )}
        {batch.failed_count > 0 && batch.status !== "processing" && (
          <DsoButton
            variant="amber"
            onClick={async () => {
              const failed = batch.runs.filter((r) => r.status === "failed");
              for (const r of failed) await triggerPipeline(r.id);
              load();
            }}
          >
            Retry {batch.failed_count} Failed
          </DsoButton>
        )}
      </div>

      {error && <DsoErrorBanner className="mb-4">{error}</DsoErrorBanner>}

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <DsoCard>
          <p className="tech-label">Status</p>
          <p className="text-sm font-medium text-bright">{batch.status}</p>
        </DsoCard>
        <DsoCard>
          <p className="tech-label">Progress</p>
          <p className="text-sm font-medium text-bright">{finished}/{batch.total_count} ({pct}%)</p>
        </DsoCard>
        <DsoCard>
          <p className="tech-label">Completed</p>
          <p className="text-sm font-medium text-teal">{batch.completed_count}</p>
        </DsoCard>
        <DsoCard>
          <p className="tech-label">Failed</p>
          <p className="text-sm font-medium text-amber">{batch.failed_count}</p>
        </DsoCard>
      </div>

      {batch.total_count > 0 && (
        <div className="mb-6">
          <DsoProgressBar
            value={batch.completed_count}
            max={batch.total_count}
            size="md"
            showPercent
          />
        </div>
      )}

      <h2 className="mb-3 font-display text-lg font-semibold text-bright">Runs</h2>
      <DsoTable
        columns={[
          {
            header: "#",
            render: (_, i) => <span className="text-muted tabular-nums">{i + 1}</span>,
          },
          {
            header: "Image",
            render: (run) => (
              <span className="max-w-32 truncate">{run.input_image_path.split("/").pop()}</span>
            ),
          },
          {
            header: "Run ID",
            render: (run) => <span className="font-mono text-xs">{run.id.slice(0, 8)}</span>,
          },
          {
            header: "Status",
            render: (run) => <RunStatusBadge status={run.status} />,
          },
          {
            header: "",
            render: (run) => (
              <div className="flex items-center gap-2">
                <Link
                  to={`/runs/${run.id}`}
                  className="text-xs font-medium text-teal hover:text-bright transition-colors"
                >
                  View
                </Link>
                {run.status === "failed" && (
                  <DsoButton
                    variant="ghost"
                    className="text-xs text-amber px-1 py-0"
                    onClick={() => handleRetryRun(run.id)}
                    disabled={retryingId === run.id}
                  >
                    {retryingId === run.id ? "Retrying..." : "Retry"}
                  </DsoButton>
                )}
              </div>
            ),
          },
        ]}
        data={batch.runs}
        keyFn={(run) => run.id}
      />
    </div>
  );
}
