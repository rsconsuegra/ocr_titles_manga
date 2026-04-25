import type { ModelDescriptorResponse, OCRRunResponse } from "./types";
import { apiFetch } from "./pipeline";

export async function getOCRModels(): Promise<ModelDescriptorResponse[]> {
  return apiFetch<ModelDescriptorResponse[]>("/api/v1/ocr/registry");
}

export async function runOCR(
  file: File,
  modelName: string,
  params: Record<string, unknown> = {},
  enableLlm: boolean = false,
): Promise<OCRRunResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("model_name", modelName);
  if (Object.keys(params).length > 0) {
    formData.append("params", JSON.stringify(params));
  }
  if (enableLlm) {
    formData.append("enable_llm", "true");
  }
  return apiFetch<OCRRunResponse>("/api/v1/ocr/run", {
    method: "POST",
    body: formData,
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
