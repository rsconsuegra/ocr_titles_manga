import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listRuns } from "../api/pipeline";
import type { PipelineRunResponse } from "../api/types";
import RunStatusBadge from "../components/RunStatusBadge";
import { EmptyState, Pagination, Table, TableSkeleton } from "../components/ui";

const STATUS_FILTERS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "processing", label: "Processing" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

const LIMIT = 20;

export default function Runs() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  /* eslint-disable react-hooks/set-state-in-effect -- data-fetching effect */
  useEffect(() => {
    setLoading(true);
    listRuns({ status: statusFilter || undefined, limit: LIMIT, offset })
      .then((data) => {
        setRuns(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [statusFilter, offset]);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    const hasActive = runs.some((r) => r.status === "pending" || r.status === "processing");
    if (!hasActive) return;
    const interval = setInterval(() => {
      listRuns({ status: statusFilter || undefined, limit: LIMIT, offset })
        .then((data) => {
          setRuns(data.items);
          setTotal(data.total);
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [runs, statusFilter, offset]);

  return (
    <div className="space-y-6">
      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => {
              setStatusFilter(f.value);
              setOffset(0);
            }}
            className={`
              px-3 py-1.5 rounded-full text-sm font-body font-medium transition-colors
              ${
                statusFilter === f.value
                  ? "bg-indigo-pale text-indigo"
                  : "bg-snow text-charcoal border border-linen hover:bg-cream"
              }
            `}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <TableSkeleton />
      ) : runs.length === 0 ? (
        <EmptyState
          title="No pipeline runs yet"
          description="Upload images and run OCR to see results here"
          actionLabel="Upload Images"
          onAction={() => navigate("/run/pipeline")}
        />
      ) : (
        <>
          <Table
            columns={[
              {
                key: "id",
                header: "Run ID",
                render: (run: PipelineRunResponse) => (
                  <span className="font-mono text-xs" title={run.id}>
                    {run.id.slice(0, 8)}
                  </span>
                ),
              },
              {
                key: "input_image_path",
                header: "Image",
                render: (run: PipelineRunResponse) => (
                  <img
                    src={`/api/v1/pipeline/runs/${run.id}/image`}
                    alt=""
                    className="size-12 rounded object-cover"
                  />
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (run: PipelineRunResponse) => <RunStatusBadge status={run.status} />,
              },
              {
                key: "created_at",
                header: "Created",
                render: (run: PipelineRunResponse) => (
                  <span className="text-xs text-sand">
                    {new Date(run.created_at).toLocaleString()}
                  </span>
                ),
              },
              {
                key: "completed_at",
                header: "Completed",
                render: (run: PipelineRunResponse) => (
                  <span className="text-xs text-sand">
                    {run.completed_at ? new Date(run.completed_at).toLocaleString() : "\u2014"}
                  </span>
                ),
              },
            ]}
            data={runs}
            onRowClick={(run) => navigate(`/runs/${(run as PipelineRunResponse).id}`)}
          />

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
