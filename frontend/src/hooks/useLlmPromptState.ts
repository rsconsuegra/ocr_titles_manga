import { useCallback, useState } from "react";

import type { LLMPromptConfig } from "../api/types";
import { LLM_DEFAULTS } from "../constants";

interface LlmPromptState {
  llmSystemPrompt: string;
  setLlmSystemPrompt: (value: string) => void;
  llmUserPrompt: string;
  setLlmUserPrompt: (value: string) => void;
  llmTemperature: number;
  setLlmTemperature: (value: number) => void;
  llmMaxOcrChars: number;
  setLlmMaxOcrChars: (value: number) => void;
  llmModel: string;
  setLlmModel: (value: string) => void;
  reasoningEnabled: boolean;
  setReasoningEnabled: (value: boolean) => void;
  showPromptSettings: boolean;
  setShowPromptSettings: (value: boolean) => void;
  toConfig: () => LLMPromptConfig | undefined;
  loadFromProfile: (data: {
    enable_llm: boolean;
    llm_provider: string;
    llm_config: LLMPromptConfig | null;
  }) => void;
}

interface LlmPromptDefaults {
  systemPrompt?: string;
  userPromptTemplate?: string;
  temperature?: number;
  maxOcrChars?: number;
}

export function useLlmPromptState(defaults?: LlmPromptDefaults): LlmPromptState {
  const [llmSystemPrompt, setLlmSystemPrompt] = useState(
    defaults?.systemPrompt ?? LLM_DEFAULTS.SYSTEM_PROMPT,
  );
  const [llmUserPrompt, setLlmUserPrompt] = useState(
    defaults?.userPromptTemplate ?? LLM_DEFAULTS.USER_PROMPT_TEMPLATE,
  );
  const [llmTemperature, setLlmTemperature] = useState(
    defaults?.temperature ?? LLM_DEFAULTS.TEMPERATURE,
  );
  const [llmMaxOcrChars, setLlmMaxOcrChars] = useState(
    defaults?.maxOcrChars ?? LLM_DEFAULTS.MAX_OCR_CHARS,
  );
  const [llmModel, setLlmModel] = useState<string>(LLM_DEFAULTS.LLM_MODEL);
  const [reasoningEnabled, setReasoningEnabled] = useState<boolean>(LLM_DEFAULTS.REASONING_ENABLED);
  const [showPromptSettings, setShowPromptSettings] = useState(false);

  const toConfig = useCallback((): LLMPromptConfig | undefined => {
    if (
      llmSystemPrompt ||
      llmUserPrompt !== LLM_DEFAULTS.USER_PROMPT_TEMPLATE ||
      llmTemperature !== LLM_DEFAULTS.TEMPERATURE ||
      llmMaxOcrChars > 0 ||
      llmModel ||
      reasoningEnabled
    ) {
      return {
        system_prompt: llmSystemPrompt,
        user_prompt_template: llmUserPrompt || LLM_DEFAULTS.USER_PROMPT_TEMPLATE,
        temperature: llmTemperature,
        max_ocr_chars: llmMaxOcrChars,
        llm_model: llmModel,
        reasoning_enabled: reasoningEnabled,
      };
    }
    return undefined;
  }, [llmSystemPrompt, llmUserPrompt, llmTemperature, llmMaxOcrChars, llmModel, reasoningEnabled]);

  const loadFromProfile = useCallback(
    (data: {
      enable_llm: boolean;
      llm_provider: string;
      llm_config: LLMPromptConfig | null;
    }) => {
      if (data.llm_config) {
        setLlmSystemPrompt(data.llm_config.system_prompt || "");
        setLlmUserPrompt(
          data.llm_config.user_prompt_template || LLM_DEFAULTS.USER_PROMPT_TEMPLATE,
        );
        setLlmTemperature(data.llm_config.temperature ?? LLM_DEFAULTS.TEMPERATURE);
        setLlmMaxOcrChars(data.llm_config.max_ocr_chars ?? LLM_DEFAULTS.MAX_OCR_CHARS);
        setLlmModel(data.llm_config.llm_model || "");
        setReasoningEnabled(data.llm_config.reasoning_enabled ?? false);
      }
    },
    [],
  );

  return {
    llmSystemPrompt,
    setLlmSystemPrompt,
    llmUserPrompt,
    setLlmUserPrompt,
    llmTemperature,
    setLlmTemperature,
    llmMaxOcrChars,
    setLlmMaxOcrChars,
    llmModel,
    setLlmModel,
    reasoningEnabled,
    setReasoningEnabled,
    showPromptSettings,
    setShowPromptSettings,
    toConfig,
    loadFromProfile,
  };
}
