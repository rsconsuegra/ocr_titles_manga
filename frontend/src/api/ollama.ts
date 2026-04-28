import type { OllamaModelInfo, OllamaStatusResponse } from "./types";

const BASE = "/api/v1/ollama";

export async function getOllamaStatus(): Promise<OllamaStatusResponse> {
  const res = await fetch(`${BASE}/status`);
  if (!res.ok) throw new Error("Failed to fetch Ollama status");
  return res.json();
}

export async function getOllamaVisionModels(): Promise<OllamaModelInfo[]> {
  const res = await fetch(`${BASE}/vision-models`);
  if (!res.ok) throw new Error("Failed to fetch Ollama vision models");
  return res.json();
}

export async function getOllamaLlmModels(): Promise<OllamaModelInfo[]> {
  const res = await fetch(`${BASE}/llm-models`);
  if (!res.ok) throw new Error("Failed to fetch Ollama LLM models");
  return res.json();
}
