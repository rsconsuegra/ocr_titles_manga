import type { PaginatedResponse, ProfileCreateRequest, ProfileResponse, ProfileUpdateRequest } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(body || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function listProfiles(
  limit = 50,
  offset = 0,
): Promise<PaginatedResponse<ProfileResponse>> {
  return apiFetch(`/api/v1/profiles?limit=${limit}&offset=${offset}`);
}

export async function getProfile(id: string): Promise<ProfileResponse> {
  return apiFetch(`/api/v1/profiles/${id}`);
}

export async function createProfile(
  data: ProfileCreateRequest,
): Promise<ProfileResponse> {
  return apiFetch("/api/v1/profiles", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function updateProfile(
  id: string,
  data: ProfileUpdateRequest,
): Promise<ProfileResponse> {
  return apiFetch(`/api/v1/profiles/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteProfile(id: string): Promise<void> {
  await apiFetch(`/api/v1/profiles/${id}`, { method: "DELETE" });
}

export async function setDefaultProfile(
  id: string,
): Promise<ProfileResponse> {
  return apiFetch(`/api/v1/profiles/${id}/set-default`, {
    method: "POST",
  });
}
