import type { QuickRunResponse } from "./types";
import { apiFetch } from "./pipeline";

export async function quickRun(
  image: string,
  options: {
    preprocessSteps?: Record<string, Record<string, unknown>>;
    ocrModels?: Record<string, Record<string, unknown>>;
    enableLlm?: boolean;
    profileId?: string;
  } = {},
): Promise<QuickRunResponse> {
  return apiFetch<QuickRunResponse>("/api/v1/run/quick", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image,
      preprocess_steps: options.preprocessSteps || {},
      ocr_models: options.ocrModels || {},
      enable_llm: options.enableLlm || false,
      profile_id: options.profileId || null,
    }),
  });
}
