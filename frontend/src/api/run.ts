import { apiFetch } from "./pipeline";
import type { LLMPromptConfig, QuickRunResponse } from "./types";

export async function quickRun(
  file: File,
  options: {
    preprocessSteps?: Record<string, Record<string, unknown>>;
    ocrModels?: Record<string, Record<string, unknown>>;
    enableLlm?: boolean;
    llmProvider?: string;
    llmModel?: string;
    llmConfig?: LLMPromptConfig;
    profileId?: string;
  } = {},
): Promise<QuickRunResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options.preprocessSteps && Object.keys(options.preprocessSteps).length > 0) {
    formData.append("preprocess_steps", JSON.stringify(options.preprocessSteps));
  }
  if (options.ocrModels && Object.keys(options.ocrModels).length > 0) {
    formData.append("ocr_models", JSON.stringify(options.ocrModels));
  }
  if (options.enableLlm) {
    formData.append("enable_llm", "true");
  }
  if (options.llmProvider) {
    formData.append("llm_provider", options.llmProvider);
  }
  if (options.llmModel) {
    formData.append("llm_model", options.llmModel);
  }
  if (options.llmConfig) {
    if (options.llmConfig.system_prompt) {
      formData.append("llm_system_prompt", options.llmConfig.system_prompt);
    }
    if (options.llmConfig.user_prompt_template) {
      formData.append("llm_user_prompt", options.llmConfig.user_prompt_template);
    }
    if (options.llmConfig.temperature !== undefined) {
      formData.append("llm_temperature", String(options.llmConfig.temperature));
    }
    if (options.llmConfig.max_ocr_chars) {
      formData.append("llm_max_ocr_chars", String(options.llmConfig.max_ocr_chars));
    }
    if (options.llmConfig.reasoning_enabled) {
      formData.append("reasoning_enabled", "true");
    }
  }
  if (options.profileId) {
    formData.append("profile_id", options.profileId);
  }
  return apiFetch<QuickRunResponse>("/api/v1/run/quick", {
    method: "POST",
    body: formData,
  });
}
