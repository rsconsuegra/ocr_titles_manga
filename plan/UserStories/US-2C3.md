# US-2C3: Pipeline Analytics Dashboard

**Sub-phase**: 2C — Pipeline Visualization
**Depends on**: US-2B3 (prompt version tracking for per-model data), US-2C1 (visualization infrastructure)
**Blocks**: None

---

## Overview

Create an analytics dashboard that visualizes pipeline performance metrics: model comparison (accuracy, speed), throughput trends, prompt version impact, and per-model confidence distributions. Uses chart components with the DSO dark theme.

---

## Implementation Details

### 1. Backend: `ocr_manga_title/api/routes/analytics.py`

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ocr_manga_title.api.deps import get_session
from ocr_manga_title.db.models import (
    PipelineRun,
    OCRResult,
    PostProcessingResult,
    PromptVersion,
)

router = APIRouter()


@router.get("/model-performance")
async def model_performance(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
):
    cutoff = func.now() - func.cast(f"{days} days", type_=func.text)
    rows = await session.execute(
        select(
            OCRResult.model_name,
            func.count(OCRResult.id).label("total_runs"),
            func.avg(OCRResult.confidence).label("avg_confidence"),
            func.avg(OCRResult.processing_time_ms).label("avg_time_ms"),
            func.count(OCRResult.error).label("error_count"),
        )
        .join(PipelineRun, OCRResult.pipeline_run_id == PipelineRun.id)
        .where(PipelineRun.status == "completed")
        .group_by(OCRResult.model_name)
    )
    return [
        {
            "model_name": r.model_name,
            "total_runs": r.total_runs,
            "avg_confidence": round(r.avg_confidence or 0, 4),
            "avg_time_ms": round(r.avg_time_ms or 0, 1),
            "error_count": r.error_count,
        }
        for r in rows
    ]


@router.get("/throughput")
async def throughput(
    session: AsyncSession = Depends(get_session),
    days: int = Query(30, ge=1, le=365),
):
    rows = await session.execute(
        select(
            func.date_trunc("day", PipelineRun.created_at).label("day"),
            func.count().label("total"),
            func.count().filter(PipelineRun.status == "completed").label("completed"),
            func.count().filter(PipelineRun.status == "failed").label("failed"),
        )
        .group_by(func.date_trunc("day", PipelineRun.created_at))
        .order_by(func.date_trunc("day", PipelineRun.created_at))
    )
    return [
        {
            "date": str(r.day),
            "total": r.total,
            "completed": r.completed,
            "failed": r.failed,
        }
        for r in rows
    ]


@router.get("/prompt-impact")
async def prompt_impact(
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(
            PostProcessingResult.prompt_version_id,
            PromptVersion.version_number,
            func.count(PostProcessingResult.id).label("total"),
            func.avg(PostProcessingResult.confidence).label("avg_confidence"),
        )
        .outerjoin(PromptVersion, PostProcessingResult.prompt_version_id == PromptVersion.id)
        .where(PostProcessingResult.processing_type == "llm")
        .group_by(
            PostProcessingResult.prompt_version_id,
            PromptVersion.version_number,
        )
    )
    return [
        {
            "prompt_version_id": r.prompt_version_id,
            "version_number": r.version_number,
            "total_extractions": r.total,
            "avg_confidence": round(r.avg_confidence or 0, 4),
        }
        for r in rows
    ]
```

### 2. `ocr_manga_title/api/app.py` (addition)

```python
from ocr_manga_title.api.routes import analytics
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
```

### 3. Frontend: `frontend/src/api/analytics.ts`

```typescript
import { apiFetch } from "./pipeline";

export interface ModelPerformance {
  model_name: string;
  total_runs: number;
  avg_confidence: number;
  avg_time_ms: number;
  error_count: number;
}

export interface ThroughputData {
  date: string;
  total: number;
  completed: number;
  failed: number;
}

export interface PromptImpact {
  prompt_version_id: number | null;
  version_number: number | null;
  total_extractions: number;
  avg_confidence: number;
}

export function getModelPerformance(days = 30) {
  return apiFetch<ModelPerformance[]>(
    `/api/v1/analytics/model-performance?days=${days}`
  );
}

export function getThroughput(days = 30) {
  return apiFetch<ThroughputData[]>(
    `/api/v1/analytics/throughput?days=${days}`
  );
}

export function getPromptImpact() {
  return apiFetch<PromptImpact[]>("/api/v1/analytics/prompt-impact");
}
```

### 4. `frontend/src/pages/PipelineAnalytics.tsx`

```tsx
import { useState, useEffect } from "react";
import {
  getModelPerformance,
  getThroughput,
  getPromptImpact,
} from "../api/analytics";
import type {
  ModelPerformance,
  ThroughputData,
  PromptImpact,
} from "../api/analytics";
import { DsoCard, DsoProgressBar } from "../components/dso";

export default function PipelineAnalytics() {
  const [models, setModels] = useState<ModelPerformance[]>([]);
  const [throughput, setThroughput] = useState<ThroughputData[]>([]);
  const [prompts, setPrompts] = useState<PromptImpact[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getModelPerformance(), getThroughput(), getPromptImpact()])
      .then(([m, t, p]) => {
        setModels(m);
        setThroughput(t);
        setPrompts(p);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-muted">Loading analytics...</p>;

  const totalRuns = throughput.reduce((sum, d) => sum + d.total, 0);
  const totalCompleted = throughput.reduce((sum, d) => sum + d.completed, 0);
  const totalFailed = throughput.reduce((sum, d) => sum + d.failed, 0);
  const successRate = totalRuns > 0 ? totalCompleted / totalRuns : 0;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-bright">Pipeline Analytics</h1>

      <div className="grid grid-cols-4 gap-4">
        <DsoCard variant="flat">
          <p className="tech-label text-xs text-muted">Total Runs</p>
          <p className="text-2xl font-bold text-bright">{totalRuns}</p>
        </DsoCard>
        <DsoCard variant="flat">
          <p className="tech-label text-xs text-muted">Completed</p>
          <p className="text-2xl font-bold text-teal">{totalCompleted}</p>
        </DsoCard>
        <DsoCard variant="flat">
          <p className="tech-label text-xs text-muted">Failed</p>
          <p className="text-2xl font-bold text-amber">{totalFailed}</p>
        </DsoCard>
        <DsoCard variant="flat">
          <p className="tech-label text-xs text-muted">Success Rate</p>
          <p className="text-2xl font-bold text-bright">
            {(successRate * 100).toFixed(1)}%
          </p>
          <DsoProgressBar value={successRate} size="sm" />
        </DsoCard>
      </div>

      <DsoCard variant="lcd">
        <h3 className="tech-label mb-4 text-xs text-muted">
          Model Performance Comparison
        </h3>
        <div className="space-y-4">
          {models.map((m) => (
            <div key={m.model_name} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-bright">{m.model_name}</span>
                <span className="text-muted">
                  {m.total_runs} runs · {(m.avg_time_ms / 1000).toFixed(1)}s avg
                </span>
              </div>
              <DsoProgressBar value={m.avg_confidence} size="sm" />
              <div className="flex justify-between text-xs text-muted">
                <span>Confidence: {(m.avg_confidence * 100).toFixed(1)}%</span>
                <span className={m.error_count > 0 ? "text-amber" : "text-teal"}>
                  {m.error_count} errors
                </span>
              </div>
            </div>
          ))}
          {models.length === 0 && (
            <p className="text-sm text-muted">No model data available yet.</p>
          )}
        </div>
      </DsoCard>

      <DsoCard variant="lcd">
        <h3 className="tech-label mb-4 text-xs text-muted">
          Daily Throughput
        </h3>
        <div className="space-y-2">
          {throughput.slice(-14).map((d) => {
            const maxVal = Math.max(...throughput.map((t) => t.total), 1);
            const completedPct = (d.completed / maxVal) * 100;
            const failedPct = (d.failed / maxVal) * 100;
            return (
              <div key={d.date} className="flex items-center gap-3 text-xs">
                <span className="w-20 shrink-0 text-muted">
                  {new Date(d.date).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
                <div className="flex-1">
                  <div className="h-4 overflow-hidden rounded bg-inset">
                    <div
                      className="h-full bg-teal"
                      style={{ width: `${completedPct}%` }}
                    />
                  </div>
                </div>
                <span className="w-12 text-right text-bright">{d.total}</span>
              </div>
            );
          })}
        </div>
      </DsoCard>

      <DsoCard variant="lcd">
        <h3 className="tech-label mb-4 text-xs text-muted">
          Prompt Version Impact
        </h3>
        <div className="space-y-3">
          {prompts.map((p) => (
            <div
              key={p.prompt_version_id || "none"}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-bright">
                {p.version_number
                  ? `v${p.version_number}`
                  : "No prompt version"}
              </span>
              <span className="text-muted">
                {p.total_extractions} extractions
              </span>
              <DsoProgressBar value={p.avg_confidence} size="sm" />
              <span className="text-bright">
                {(p.avg_confidence * 100).toFixed(1)}%
              </span>
            </div>
          ))}
          {prompts.length === 0 && (
            <p className="text-sm text-muted">No prompt impact data yet.</p>
          )}
        </div>
      </DsoCard>
    </div>
  );
}
```

### 5. `frontend/src/App.tsx` (addition)

```tsx
import PipelineAnalytics from "./pages/PipelineAnalytics";

<Route path="/analytics" element={<PipelineAnalytics />} />

// In "Playground" dropdown:
<Link to="/analytics">Analytics</Link>
```

---

## Acceptance Criteria

- [ ] `/analytics` page shows summary cards: total runs, completed, failed, success rate
- [ ] Model performance section: per-model bars showing confidence, run count, avg time, errors
- [ ] Daily throughput chart: horizontal bars for last 14 days with completed/failed breakdown
- [ ] Prompt version impact: comparison of avg confidence per prompt version
- [ ] `GET /api/v1/analytics/model-performance?days=N` returns per-model aggregated stats
- [ ] `GET /api/v1/analytics/throughput?days=N` returns daily run counts
- [ ] `GET /api/v1/analytics/prompt-impact` returns confidence by prompt version
- [ ] Graceful empty states when no data available
- [ ] DSO dark theme (LCD screens, progress bars, tech labels)

---

## Test Specifications

**File**: `tests/test_api/test_analytics_routes.py`

Tests:
- `test_model_performance_returns_per_model_stats` — seed OCR results; verify avg_confidence and avg_time_ms
- `test_throughput_returns_daily_counts` — seed pipeline runs across days; verify grouped by day
- `test_prompt_impact_groups_by_version` — seed post-processing with prompt_version_id; verify grouping
- `test_model_performance_respects_days_param` — seed old + recent runs; verify `days=7` filters correctly
- `test_empty_data_returns_empty_lists` — no data; verify all endpoints return `[]`

Manual UI testing:
- Navigate to `/analytics` with no data — verify empty states
- Run some pipelines, then check analytics — verify charts populated
