import type {
  PreviewPipelineResponse,
  PreviewStepResponse,
  StepDescriptor,
} from "./types";
import { apiFetch } from "./pipeline";

export async function getPreprocessSteps(): Promise<StepDescriptor[]> {
  return apiFetch<StepDescriptor[]>("/api/v1/preprocess/steps");
}

export async function previewStep(
  image: string,
  stepName: string,
  params: Record<string, unknown> = {},
): Promise<PreviewStepResponse> {
  return apiFetch<PreviewStepResponse>("/api/v1/preprocess/preview/step", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image, step_name: stepName, params }),
  });
}

export async function previewPipeline(
  image: string,
  steps: Record<string, Record<string, unknown>> = {},
): Promise<PreviewPipelineResponse> {
  return apiFetch<PreviewPipelineResponse>("/api/v1/preprocess/preview/pipeline", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image, steps }),
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
