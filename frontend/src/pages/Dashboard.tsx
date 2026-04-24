import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDashboardStats, listRuns } from "../api/pipeline";
import type { PipelineRunResponse } from "../api/types";
import {
  DsoBadge,
  DsoButton,
  DsoCard,
  DsoScrew,
  DsoVentGrille,
} from "../components/dso";

const statusVariant = {
  pending: "pending" as const,
  processing: "processing" as const,
  completed: "completed" as const,
  failed: "failed" as const,
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<{
    total: number;
    completed: number;
    failed: number;
    processing: number;
    pending: number;
    success_rate: number;
  } | null>(null);
  const [recentRuns, setRecentRuns] = useState<PipelineRunResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getDashboardStats(), listRuns({ limit: 5 })])
      .then(([s, runs]) => {
        setStats(s);
        setRecentRuns(runs.items);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="tech-label-bright breathing">Initializing...</span>
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="tech-label text-amber">Signal Lost</span>
      </div>
    );
  }

  const metrics = [
    { label: "TOTAL", value: stats.total, led: "led-off" },
    { label: "COMPLETED", value: stats.completed, led: "led-active" },
    { label: "FAILED", value: stats.failed, led: "led-amber" },
    { label: "PROCESSING", value: stats.processing, led: "led-active" },
    { label: "PENDING", value: stats.pending, led: "led-off" },
    { label: "SUCCESS", value: `${stats.success_rate}%`, led: "led-active" },
  ];

  return (
    <div className="mx-auto max-w-6xl">
      <div className="neo-panel relative p-6">
        <DsoScrew className="absolute left-3 top-3" />
        <DsoScrew className="absolute right-3 top-3" />
        <DsoScrew className="absolute bottom-3 left-3" />
        <DsoScrew className="absolute bottom-3 right-3" />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {/* Top-Left: Hero */}
          <DsoCard variant="inset" className="relative flex flex-col justify-between">
            <DsoScrew className="absolute left-2 top-2" />
            <DsoScrew className="absolute right-2 top-2" />
            <div>
              <p className="tech-label mb-2 text-teal">Oscilloscope Control Panel</p>
              <h1
                className="font-display font-bold text-bright leading-tight"
                style={{ fontSize: "clamp(1.75rem, 3vw, 2.75rem)" }}
              >
                MANGA OCR
              </h1>
              <p className="mt-2 text-sm text-muted">
                Digital Storage OCR Pipeline &mdash; Real-time manga text extraction engine
              </p>
            </div>
            <div className="mt-4 flex items-end justify-between">
              <DsoVentGrille />
              <div className="flex items-center gap-2">
                <span className="led led-active" />
                <span className="tech-label-bright">Online</span>
              </div>
            </div>
          </DsoCard>

          {/* Top-Right: Service Matrix LCD */}
          <DsoCard variant="lcd" className="lcd-graticule">
            <div className="absolute inset-0 z-0 rounded-lg border border-teal/10" />
            <div className="relative z-10">
              <p className="tech-label mb-3 text-teal">Service Matrix</p>
              <div className="grid grid-cols-3 gap-px">
                {metrics.map((m) => (
                  <div
                    key={m.label}
                    className="flex flex-col items-center gap-1 rounded-sm px-2 py-3 transition-colors duration-150 hover:bg-teal/6"
                  >
                    <span className={`led ${m.led}`} />
                    <span className="font-display text-xl font-bold text-bright">
                      {m.value}
                    </span>
                    <span className="tech-label">{m.label}</span>
                  </div>
                ))}
              </div>
              <div className="mt-3 border-t border-teal/12 pt-2">
                <div className="flex items-center justify-between">
                  <span className="tech-label">Pipeline Status</span>
                  <div className="flex items-center gap-2">
                    <span className="led led-active" />
                    <span className="text-xs text-teal">Nominal</span>
                  </div>
                </div>
              </div>
            </div>
          </DsoCard>

          {/* Bottom-Left: Tactical Controls */}
          <DsoCard variant="flat">
            <p className="tech-label mb-4 text-teal">Tactical Controls</p>
            <div className="flex flex-wrap gap-3">
              <DsoButton onClick={() => navigate("/upload")}>
                Upload Images
              </DsoButton>
              <DsoButton variant="secondary" onClick={() => navigate("/run/quick")}>
                Quick Run
              </DsoButton>
              <DsoButton variant="secondary" onClick={() => navigate("/playground/ocr")}>
                OCR Test
              </DsoButton>
              <DsoButton variant="secondary" onClick={() => navigate("/playground/preprocess")}>
                Preprocess
              </DsoButton>
            </div>
            <div className="mt-5 grid grid-cols-3 gap-4 border-t border-highlight/20 pt-4">
              <div>
                <p className="font-display text-lg font-bold text-bright">{stats.total}</p>
                <p className="tech-label">Total Ops</p>
              </div>
              <div>
                <p className="font-display text-lg font-bold text-teal">{stats.success_rate}%</p>
                <p className="tech-label">Accuracy</p>
              </div>
              <div>
                <p className="font-display text-lg font-bold text-amber">
                  {stats.failed + stats.processing}
                </p>
                <p className="tech-label">Alerts</p>
              </div>
            </div>
          </DsoCard>

          {/* Bottom-Right: Recent Runs LCD Readout */}
          <DsoCard variant="lcd" className="lcd-graticule">
            <div className="relative z-10">
              <p className="tech-label mb-3 text-teal">Recent Runs</p>
              {recentRuns.length === 0 ? (
                <p className="text-sm text-muted py-4 text-center">No signal detected</p>
              ) : (
                <div className="space-y-1">
                  {recentRuns.map((run, i) => (
                    <button
                      key={run.id}
                      onClick={() => navigate(`/runs/${run.id}`)}
                      className="flex w-full items-center gap-3 rounded px-2 py-1.5 text-left transition-colors duration-100 hover:bg-teal/6"
                    >
                      <span className="tech-label w-4 text-right tabular-nums">{i + 1}</span>
                      <span className="font-mono text-xs text-bright/80">{run.id.slice(0, 8)}</span>
                      <span className="flex-1 truncate text-xs text-muted">
                        {run.input_image_path.split("/").pop()}
                      </span>
                      <DsoBadge
                        variant={statusVariant[run.status as keyof typeof statusVariant] ?? "default"}
                        led={true}
                        className="text-[10px]"
                      >
                        {run.status}
                      </DsoBadge>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </DsoCard>
        </div>
      </div>
    </div>
  );
}
