import { apiFetch } from "./pipeline";
import type { CatalogEntryResponse, PaginatedResponse } from "./types";

export function getCatalogExportUrl(): string {
  const base = import.meta.env.VITE_API_URL || "";
  return `${base}/api/v1/catalog/export`;
}

export async function listCatalog(params?: {
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}): Promise<PaginatedResponse<CatalogEntryResponse>> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.search) searchParams.set("search", params.search);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/catalog${qs ? `?${qs}` : ""}`);
}

export async function updateCatalogEntry(
  entryId: string,
  data: { status?: string; title_en?: string; title_ja?: string; code?: string },
): Promise<CatalogEntryResponse> {
  return apiFetch<CatalogEntryResponse>(`/api/v1/catalog/${entryId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
