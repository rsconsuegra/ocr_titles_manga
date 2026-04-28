export const OLLAMA_VISION_MODEL = "ollama_vision";

export const LLM_DEFAULTS = {
  PROVIDER: "openrouter",
  SYSTEM_PROMPT: "",
  USER_PROMPT_TEMPLATE: "{ocr_text}",
  TEMPERATURE: 0.1,
  MAX_OCR_CHARS: 0,
} as const;
