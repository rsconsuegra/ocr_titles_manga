import type { OllamaModelInfo, OllamaStatusResponse, OpenRouterModel } from "../api/types";
import { Select } from "./ui";

interface LlmConfigSectionProps {
  enableLlm: boolean;
  onEnableLlmChange: (value: boolean) => void;
  llmDisabled?: boolean;
  llmDisabledReason?: string;
  llmProvider: string;
  onLlmProviderChange: (value: string) => void;
  llmModel: string;
  onLlmModelChange: (value: string) => void;
  ollamaModels: OllamaModelInfo[];
  ollamaStatus: OllamaStatusResponse | null;
  openRouterModels: OpenRouterModel[];
  openRouterModel: string;
  onOpenRouterModelChange: (value: string) => void;
  reasoningEnabled: boolean;
  onReasoningEnabledChange: (value: boolean) => void;
  radioName: string;
  label?: string;
}

export default function LlmConfigSection({
  enableLlm,
  onEnableLlmChange,
  llmDisabled = false,
  llmDisabledReason = "Disabled: Ollama Vision handles extraction directly.",
  llmProvider,
  onLlmProviderChange,
  llmModel,
  onLlmModelChange,
  ollamaModels,
  ollamaStatus,
  openRouterModels,
  openRouterModel,
  onOpenRouterModelChange,
  reasoningEnabled,
  onReasoningEnabledChange,
  radioName,
  label = "Post-process with LLM",
}: LlmConfigSectionProps) {
  return (
    <div className="space-y-2">
      <label
        className={`flex items-center gap-2 text-sm ${llmDisabled ? "cursor-not-allowed text-sand" : "text-charcoal"}`}
      >
        <input
          type="checkbox"
          checked={enableLlm}
          onChange={(e) => onEnableLlmChange(e.target.checked)}
          disabled={llmDisabled}
          className="rounded border-linen bg-linen accent-indigo disabled:opacity-50"
        />
        {label}
      </label>
      {llmDisabled && <p className="text-xs text-sand">{llmDisabledReason}</p>}
      {enableLlm && !llmDisabled && (
        <div className="ml-6 space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-xs text-sand">Provider:</span>
            <label className="flex items-center gap-1 text-xs text-charcoal">
              <input
                type="radio"
                name={radioName}
                checked={llmProvider === "openrouter"}
                onChange={() => onLlmProviderChange("openrouter")}
                className="accent-indigo"
              />
              OpenRouter
            </label>
            <label className="flex items-center gap-1 text-xs text-charcoal">
              <input
                type="radio"
                name={radioName}
                checked={llmProvider === "ollama"}
                onChange={() => onLlmProviderChange("ollama")}
                className="accent-indigo"
              />
              Ollama
            </label>
          </div>
          {llmProvider === "openrouter" && openRouterModels.length > 0 && (
            <Select
              label="Model"
              value={openRouterModel}
              onChange={(e) => onOpenRouterModelChange(e.target.value)}
              options={[
                { value: "", label: "Default (Gemini 2.5 Flash)" },
                ...openRouterModels.map((m) => ({ value: m.id, label: m.label })),
              ]}
            />
          )}
          {llmProvider === "openrouter" && (
            <label className="flex items-center gap-2 text-xs text-charcoal">
              <input
                type="checkbox"
                checked={reasoningEnabled}
                onChange={(e) => onReasoningEnabledChange(e.target.checked)}
                className="rounded border-linen bg-linen accent-indigo"
              />
              Enable reasoning
            </label>
          )}
          {llmProvider === "ollama" && ollamaStatus?.configured && ollamaModels.length > 0 && (
            <Select
              label="LLM Model"
              value={llmModel}
              onChange={(e) => onLlmModelChange(e.target.value)}
              options={[
                { value: "", label: "Default" },
                ...ollamaModels.map((m) => ({ value: m.name, label: m.name })),
              ]}
            />
          )}
          {llmProvider === "ollama" && ollamaStatus?.configured && ollamaModels.length === 0 && (
            <p className="text-xs text-sand">
              No Ollama models found. Make sure Ollama is running.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
