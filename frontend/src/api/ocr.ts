import type { ModelDescriptorResponse, OCRRunResponse } from "./types";
import { apiFetch } from "./pipeline";

export async function getOCRModels(): Promise<ModelDescriptorResponse[]> {
  return apiFetch<ModelDescriptorResponse[]>("/api/v1/ocr/registry");
}

export async function runOCR(
  image: string,
  modelName: string,
  params: Record<string, unknown> = {},
  enableLlm: boolean = false,
): Promise<OCRRunResponse> {
  return apiFetch<OCRRunResponse>("/api/v1/ocr/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image, model_name: modelName, params, enable_llm: enableLlm }),
  });
}

export async function exportOCRConfig(
  models: Record<string, Record<string, unknown>> = {},
): Promise<{ yaml: string }> {
  return apiFetch<{ yaml: string }>("/api/v1/ocr/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ models }),
  });
}
