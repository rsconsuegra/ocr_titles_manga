import type { QuickRunResponse } from "./types";
import { apiFetch } from "./pipeline";

export async function quickRun(
  file: File,
  options: {
    preprocessSteps?: Record<string, Record<string, unknown>>;
    ocrModels?: Record<string, Record<string, unknown>>;
    enableLlm?: boolean;
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
  if (options.profileId) {
    formData.append("profile_id", options.profileId);
  }
  return apiFetch<QuickRunResponse>("/api/v1/run/quick", {
    method: "POST",
    body: formData,
  });
}
