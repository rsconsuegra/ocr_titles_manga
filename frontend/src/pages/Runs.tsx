import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { listRuns } from "../api/pipeline";
import type { PipelineRunResponse } from "../api/types";
import { DsoPagination, DsoSelect, DsoTable } from "../components/dso";
import RunStatusBadge from "../components/RunStatusBadge";

const STATUSES = ["", "pending", "processing", "completed", "failed", "cancelled"];
const LIMIT = 20;

export default function Runs() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    listRuns({ status: statusFilter || undefined, limit: LIMIT, offset })
      .then((data) => {
        setRuns(data.items);
        setTotal(data.total);
      })
      .finally(() => setLoading(false));
  }, [statusFilter, offset]);

  useEffect(() => {
    const hasActive = runs.some((r) => r.status === "pending" || r.status === "processing");
    if (!hasActive) return;
    const interval = setInterval(() => {
      listRuns({ status: statusFilter || undefined, limit: LIMIT, offset }).then((data) => {
        setRuns(data.items);
        setTotal(data.total);
      });
    }, 10000);
    return () => clearInterval(interval);
  }, [runs, statusFilter, offset]);

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">Pipeline Runs</h1>
        <DsoSelect
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setOffset(0);
          }}
        >
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All Statuses"}
            </option>
          ))}
        </DsoSelect>
      </div>

      {loading ? (
        <p className="tech-label breathing">Scanning...</p>
      ) : runs.length === 0 ? (
        <p className="text-sm text-muted">No pipeline runs detected.</p>
      ) : (
        <>
          <DsoTable
            columns={[
              {
                header: "Run ID",
                render: (run: PipelineRunResponse) => (
                  <span className="font-mono text-xs" title={run.id}>{run.id.slice(0, 8)}</span>
                ),
              },
              {
                header: "Image",
                render: (run: PipelineRunResponse) => (
                  <span className="max-w-48 truncate">{run.input_image_path.split("/").pop()}</span>
                ),
              },
              {
                header: "Status",
                render: (run: PipelineRunResponse) => <RunStatusBadge status={run.status} />,
              },
              {
                header: "Created",
                render: (run: PipelineRunResponse) => (
                  <span className="text-xs text-muted">{new Date(run.created_at).toLocaleString()}</span>
                ),
              },
              {
                header: "Completed",
                render: (run: PipelineRunResponse) => (
                  <span className="text-xs text-muted">
                    {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
                  </span>
                ),
              },
            ]}
            data={runs}
            keyFn={(run) => run.id}
            onRowClick={(run) => navigate(`/runs/${run.id}`)}
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
