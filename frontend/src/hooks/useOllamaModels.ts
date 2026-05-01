import { useEffect, useState } from "react";

import { getOllamaLlmModels, getOllamaStatus, getOllamaVisionModels } from "../api/ollama";
import type { OllamaModelInfo, OllamaStatusResponse } from "../api/types";

interface OllamaModelsData {
  status: OllamaStatusResponse | null;
  visionModels: OllamaModelInfo[];
  llmModels: OllamaModelInfo[];
}

export function useOllamaModels(): OllamaModelsData {
  const [status, setStatus] = useState<OllamaStatusResponse | null>(null);
  const [visionModels, setVisionModels] = useState<OllamaModelInfo[]>([]);
  const [llmModels, setLlmModels] = useState<OllamaModelInfo[]>([]);

  useEffect(() => {
    getOllamaStatus()
      .then((s) => {
        setStatus(s);
        if (s.configured) {
          getOllamaVisionModels()
            .then(setVisionModels)
            .catch(() => {});
          getOllamaLlmModels()
            .then(setLlmModels)
            .catch(() => {});
        }
      })
      .catch(() => {});
  }, []);

  return { status, visionModels, llmModels };
}
