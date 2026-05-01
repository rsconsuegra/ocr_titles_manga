import type {
  CredentialInfo,
  CredentialValidateResponse,
  OllamaSettingsResponse,
  OllamaUrlUpdateResponse,
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

export async function getOllamaSettings(): Promise<OllamaSettingsResponse> {
  return apiFetch("/api/v1/settings/ollama");
}

export async function updateOllamaUrl(params: {
  base_url: string;
  default_model?: string;
  default_vision_model?: string;
}): Promise<OllamaUrlUpdateResponse> {
  return apiFetch<OllamaUrlUpdateResponse>("/api/v1/settings/ollama", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
}

export async function pingOllamaUrl(base_url: string): Promise<OllamaUrlUpdateResponse> {
  return apiFetch<OllamaUrlUpdateResponse>("/api/v1/settings/ollama/ping", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ base_url }),
  });
}

export async function getCredential(service: string): Promise<CredentialInfo> {
  return apiFetch(`/api/v1/settings/credentials/${service}`);
}

export async function updateCredential(
  service: string,
  api_key: string,
): Promise<CredentialValidateResponse> {
  return apiFetch<CredentialValidateResponse>(`/api/v1/settings/credentials/${service}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key }),
  });
}

export async function deleteCredential(service: string): Promise<{ deactivated: boolean }> {
  return apiFetch(`/api/v1/settings/credentials/${service}`, { method: "DELETE" });
}

export async function validateCredential(
  service: string,
  api_key: string,
): Promise<CredentialValidateResponse> {
  return apiFetch<CredentialValidateResponse>(`/api/v1/settings/credentials/${service}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key }),
  });
}
