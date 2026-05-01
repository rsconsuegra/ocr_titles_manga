import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getDashboardStats, listRuns } from "../api/pipeline";
import type { PipelineRunResponse } from "../api/types";
import { Badge, Button, Card, DashboardSkeleton, EmptyState, Table } from "../components/ui";

const statusVariant = {
  pending: "pending" as const,
  processing: "processing" as const,
  completed: "completed" as const,
  failed: "failed" as const,
  cancelled: "cancelled" as const,
};

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<{
    total: number;
    completed: number;
    failed: number;
    processing: number;
    pending: number;
    cancelled: number;
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

  if (loading) return <DashboardSkeleton />;

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="text-sand">Unable to load dashboard data</span>
      </div>
    );
  }

  const quickActions = [
    {
      title: "Upload Images",
      description: "Upload manga images for batch OCR processing",
      route: "/run/pipeline",
    },
    {
      title: "Quick Run",
      description: "Run the full pipeline on a single image",
      route: "/run/quick",
    },
    {
      title: "OCR Playground",
      description: "Test individual OCR models on sample images",
      route: "/playground/ocr",
    },
  ];

  const statCards = [
    { label: "Total Runs", value: stats.total },
    { label: "Completed", value: stats.completed },
    { label: "Failed", value: stats.failed },
    { label: "Avg Confidence", value: `${stats.success_rate}%` },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-semibold text-ink mb-1">Welcome to Manga OCR</h1>
        <p className="text-sand font-body text-sm">Extract and catalog manga titles with OCR</p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {quickActions.map((action) => (
          <Card key={action.route} hover>
            <h3 className="font-display text-base font-semibold text-ink mb-1">{action.title}</h3>
            <p className="text-sm text-sand mb-4">{action.description}</p>
            <Button variant="ghost" onClick={() => navigate(action.route)}>
              Go &rarr;
            </Button>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Card key={stat.label} padding="sm">
            <span className="label-text">{stat.label}</span>
            <p className="font-display text-2xl font-bold text-ink mt-1">{stat.value}</p>
          </Card>
        ))}
      </div>

      <Card>
        <Card.Header title="Recent Runs">
          <Button variant="ghost" onClick={() => navigate("/runs")}>
            View All &rarr;
          </Button>
        </Card.Header>
        {recentRuns.length === 0 ? (
          <EmptyState
            title="No recent runs"
            description="Upload images to start processing"
            actionLabel="Upload Images"
            onAction={() => navigate("/run/pipeline")}
          />
        ) : (
          <Table
            columns={[
              {
                key: "input_image_path",
                header: "Image",
                render: (run: PipelineRunResponse) => (
                  <span className="truncate max-w-48 block">
                    {run.input_image_path.split("/").pop()}
                  </span>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (run: PipelineRunResponse) => (
                  <Badge
                    status={statusVariant[run.status as keyof typeof statusVariant] ?? "default"}
                    size="sm"
                  >
                    {run.status}
                  </Badge>
                ),
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
            ]}
            data={recentRuns}
            onRowClick={(run) => navigate(`/runs/${(run as PipelineRunResponse).id}`)}
            emptyMessage="No recent runs"
          />
        )}
      </Card>
    </div>
  );
}
