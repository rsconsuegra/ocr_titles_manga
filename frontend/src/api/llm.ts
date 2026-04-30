import { apiFetch } from "./pipeline";
import type { LLMProvidersResponse, OpenRouterModel } from "./types";

export async function getLLMProviders(): Promise<LLMProvidersResponse> {
  return apiFetch<LLMProvidersResponse>("/api/v1/llm/providers");
}

export async function getOpenRouterModels(): Promise<OpenRouterModel[]> {
  return apiFetch<OpenRouterModel[]>("/api/v1/llm/openrouter/models");
}
