import { apiFetch } from "./pipeline";
import type { LLMPromptConfig, ModelDescriptorResponse, OCRRunResponse } from "./types";

export async function getOCRModels(): Promise<ModelDescriptorResponse[]> {
  return apiFetch<ModelDescriptorResponse[]>("/api/v1/ocr/registry");
}

export async function runOCR(
  file: File,
  modelName: string,
  params: Record<string, unknown> = {},
  enableLlm: boolean = false,
  llmProvider: string = "openrouter",
  llmModel: string = "",
  llmConfig?: LLMPromptConfig,
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
  formData.append("llm_provider", llmProvider);
  if (llmModel) {
    formData.append("llm_model", llmModel);
  }
  if (llmConfig) {
    if (llmConfig.system_prompt) {
      formData.append("llm_system_prompt", llmConfig.system_prompt);
    }
    if (llmConfig.user_prompt_template) {
      formData.append("llm_user_prompt", llmConfig.user_prompt_template);
    }
    if (llmConfig.temperature !== undefined) {
      formData.append("llm_temperature", String(llmConfig.temperature));
    }
    if (llmConfig.max_ocr_chars) {
      formData.append("llm_max_ocr_chars", String(llmConfig.max_ocr_chars));
    }
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
