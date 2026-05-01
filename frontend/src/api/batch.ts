import type { BatchRunDetailResponse, BatchRunResponse, PaginatedResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  return res.json();
}

export async function createBatch(
  files: File[],
  name?: string,
  profileId?: string,
): Promise<BatchRunDetailResponse> {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  if (name) formData.append("name", name);
  if (profileId) formData.append("profile_id", profileId);
  return apiFetch<BatchRunDetailResponse>("/api/v1/batches", {
    method: "POST",
    body: formData,
  });
}

export async function triggerBatch(batchId: string): Promise<BatchRunResponse> {
  return apiFetch<BatchRunResponse>(`/api/v1/batches/${batchId}/trigger`, {
    method: "POST",
  });
}

export async function listBatches(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<BatchRunResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/batches${qs ? `?${qs}` : ""}`);
}

export async function getBatchDetail(batchId: string): Promise<BatchRunDetailResponse> {
  return apiFetch<BatchRunDetailResponse>(`/api/v1/batches/${batchId}`);
}
