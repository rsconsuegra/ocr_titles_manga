import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { getBatchDetail, triggerBatch } from "../api/batch";
import { triggerPipeline } from "../api/pipeline";
import type { BatchRunDetailResponse } from "../api/types";
import RunStatusBadge from "../components/RunStatusBadge";
import {
  Badge,
  BatchDetailSkeleton,
  Button,
  Card,
  ErrorBanner,
  ProgressBar,
  Table,
} from "../components/ui";

const statusVariant: Record<string, "completed" | "processing" | "failed" | "pending" | "default"> =
  {
    completed: "completed",
    processing: "processing",
    partial_failure: "failed",
    failed: "failed",
    pending: "pending",
  };

export default function BatchRunDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [batch, setBatch] = useState<BatchRunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getBatchDetail(id);
      setBatch(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load batch");
    } finally {
      setLoading(false);
    }
  }, [id]);

  /* eslint-disable react-hooks/set-state-in-effect -- data-fetching effect */
  useEffect(() => {
    load();
  }, [load]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const isProcessing = batch?.status === "processing";

  useEffect(() => {
    if (!isProcessing) return;
    const interval = setInterval(load, 3000);
    return () => clearInterval(interval);
  }, [isProcessing, load]);

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

  if (loading) return <BatchDetailSkeleton />;
  if (!batch) return <ErrorBanner message="Batch not found" />;

  const finished = batch.completed_count + batch.failed_count;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <Link
            to="/batches"
            className="text-sm text-indigo hover:text-indigo/70 transition-colors"
          >
            &larr; All Batches
          </Link>
          <h1 className="mt-1 font-display text-xl font-bold text-ink">
            {batch.name || "Untitled Batch"}
          </h1>
        </div>
        {batch.status === "pending" && (
          <Button onClick={handleTrigger} disabled={triggering}>
            {triggering ? "Triggering..." : "Process All"}
          </Button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <Card className="mb-6">
        <Card.Header title="Progress Overview">
          {batch.failed_count > 0 && batch.status !== "processing" && (
            <Button
              variant="secondary"
              onClick={async () => {
                const failed = batch.runs.filter((r) => r.status === "failed");
                for (const r of failed) await triggerPipeline(r.id);
                load();
              }}
            >
              Retry {batch.failed_count} Failed
            </Button>
          )}
        </Card.Header>
        <div className="flex items-center gap-4 mb-3">
          <Badge status={statusVariant[batch.status] ?? "default"}>{batch.status}</Badge>
          <span className="text-sm text-sand">
            {finished}/{batch.total_count} runs
          </span>
        </div>
        <ProgressBar
          value={batch.total_count > 0 ? (batch.completed_count / batch.total_count) * 100 : 0}
          size="md"
          showLabel
        />
        <div className="mt-3 grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="label-text">Completed</p>
            <p className="text-sm font-medium text-indigo">{batch.completed_count}</p>
          </div>
          <div>
            <p className="label-text">Failed</p>
            <p className="text-sm font-medium text-vermillion">{batch.failed_count}</p>
          </div>
          <div>
            <p className="label-text">Pending</p>
            <p className="text-sm font-medium text-charcoal">
              {Math.max(0, batch.total_count - finished)}
            </p>
          </div>
        </div>
      </Card>

      <h2 className="mb-3 font-display text-lg font-semibold text-ink">Runs</h2>
      <Table
        onRowClick={(run) => navigate(`/runs/${(run as (typeof batch.runs)[number]).id}`)}
        columns={[
          {
            key: "id",
            header: "#",
            render: (run) => (
              <span className="text-sand tabular-nums">
                {batch.runs.indexOf(run as (typeof batch.runs)[number]) + 1}
              </span>
            ),
          },
          {
            key: "input_image_path",
            header: "Image",
            render: (run) => (
              <span className="max-w-32 truncate">
                {(run as (typeof batch.runs)[number]).input_image_path.split("/").pop()}
              </span>
            ),
          },
          {
            key: "id",
            header: "Run ID",
            render: (run) => (
              <span className="font-mono text-xs">
                {(run as (typeof batch.runs)[number]).id.slice(0, 8)}
              </span>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (run) => (
              <RunStatusBadge status={(run as (typeof batch.runs)[number]).status} />
            ),
          },
          {
            key: "id",
            header: "",
            render: (run) => {
              const r = run as (typeof batch.runs)[number];
              if (r.status !== "failed") return null;
              return (
                <Button
                  variant="ghost"
                  className="text-xs text-vermillion px-1 py-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRetryRun(r.id);
                  }}
                  disabled={retryingId === r.id}
                >
                  {retryingId === r.id ? "Retrying..." : "Retry"}
                </Button>
              );
            },
          },
        ]}
        data={batch.runs}
      />
    </div>
  );
}
