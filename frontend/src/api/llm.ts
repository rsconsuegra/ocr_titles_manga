import { apiFetch } from "./pipeline";
import type { LLMProvidersResponse } from "./types";

export async function getLLMProviders(): Promise<LLMProvidersResponse> {
  return apiFetch<LLMProvidersResponse>("/api/v1/llm/providers");
}
