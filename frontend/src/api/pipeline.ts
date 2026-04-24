import type {
  PaginatedResponse,
  PipelineRunResponse,
  PostProcessingResultDetail,
  RunDetailResponse,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export { apiFetch };

export async function uploadImages(
  files: File[],
  profileId?: string,
): Promise<PipelineRunResponse[]> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  const params = profileId ? `?profile_id=${encodeURIComponent(profileId)}` : "";
  return apiFetch<PipelineRunResponse[]>(`/api/v1/inputs/upload${params}`, {
    method: "POST",
    body: formData,
  });
}

export async function triggerPipeline(runId: string): Promise<{ message: string; run_id: string }> {
  return apiFetch("/api/v1/pipeline/run/" + runId, { method: "POST" });
}

export async function listRuns(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<PipelineRunResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/pipeline/runs${qs ? `?${qs}` : ""}`);
}

export async function getRunDetail(runId: string): Promise<RunDetailResponse> {
  return apiFetch<RunDetailResponse>(`/api/v1/pipeline/runs/${runId}`);
}

export async function overrideResult(
  resultId: string,
  data: { title_en?: string; title_ja?: string; code?: string },
): Promise<PostProcessingResultDetail> {
  return apiFetch<PostProcessingResultDetail>(`/api/v1/results/${resultId}/override`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getDashboardStats(): Promise<{
  total: number;
  completed: number;
  failed: number;
  processing: number;
  pending: number;
  success_rate: number;
}> {
  const [all, completed, failed, processing, pending] = await Promise.all([
    listRuns({ limit: 1 }),
    listRuns({ status: "completed", limit: 1 }),
    listRuns({ status: "failed", limit: 1 }),
    listRuns({ status: "processing", limit: 1 }),
    listRuns({ status: "pending", limit: 1 }),
  ]);
  const totalFinished = completed.total + failed.total;
  return {
    total: all.total,
    completed: completed.total,
    failed: failed.total,
    processing: processing.total,
    pending: pending.total,
    success_rate: totalFinished > 0 ? Math.round((completed.total / totalFinished) * 100) : 0,
  };
}
