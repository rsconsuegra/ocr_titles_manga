import { apiFetch } from "./pipeline";
import type { PreviewPipelineResponse, PreviewStepResponse, StepDescriptor } from "./types";

export async function getPreprocessSteps(): Promise<StepDescriptor[]> {
  return apiFetch<StepDescriptor[]>("/api/v1/preprocess/steps");
}

export async function previewStep(
  file: File,
  stepName: string,
  params: Record<string, unknown> = {},
): Promise<PreviewStepResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("step_name", stepName);
  if (Object.keys(params).length > 0) {
    formData.append("params", JSON.stringify(params));
  }
  return apiFetch<PreviewStepResponse>("/api/v1/preprocess/preview/step", {
    method: "POST",
    body: formData,
  });
}

export async function previewPipeline(
  file: File,
  steps: Record<string, Record<string, unknown>> = {},
): Promise<PreviewPipelineResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (Object.keys(steps).length > 0) {
    formData.append("steps", JSON.stringify(steps));
  }
  return apiFetch<PreviewPipelineResponse>("/api/v1/preprocess/preview/pipeline", {
    method: "POST",
    body: formData,
  });
}

export async function exportPipeline(
  steps: Record<string, Record<string, unknown>> = {},
): Promise<{ yaml: string }> {
  return apiFetch<{ yaml: string }>("/api/v1/preprocess/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ steps }),
  });
}
