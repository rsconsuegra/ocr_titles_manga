import type { OllamaModelInfo, OllamaStatusResponse } from "../api/types";
import { DsoSelect } from "./dso";

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
  radioName,
  label = "Post-process with LLM",
}: LlmConfigSectionProps) {
  return (
    <div className="space-y-2">
      <label
        className={`flex items-center gap-2 text-sm ${llmDisabled ? "cursor-not-allowed text-muted" : "text-bright"}`}
      >
        <input
          type="checkbox"
          checked={enableLlm}
          onChange={(e) => onEnableLlmChange(e.target.checked)}
          disabled={llmDisabled}
          className="rounded border-highlight/40 bg-inset accent-teal disabled:opacity-50"
        />
        {label}
      </label>
      {llmDisabled && <p className="text-xs text-muted">{llmDisabledReason}</p>}
      {enableLlm && !llmDisabled && (
        <div className="ml-6 space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted">Provider:</span>
            <label className="flex items-center gap-1 text-xs text-bright">
              <input
                type="radio"
                name={radioName}
                checked={llmProvider === "openrouter"}
                onChange={() => onLlmProviderChange("openrouter")}
                className="accent-teal"
              />
              OpenRouter
            </label>
            <label className="flex items-center gap-1 text-xs text-bright">
              <input
                type="radio"
                name={radioName}
                checked={llmProvider === "ollama"}
                onChange={() => onLlmProviderChange("ollama")}
                className="accent-teal"
              />
              Ollama
            </label>
          </div>
          {llmProvider === "ollama" && ollamaStatus?.configured && ollamaModels.length > 0 && (
            <DsoSelect
              label="LLM Model"
              value={llmModel}
              onChange={(e) => onLlmModelChange(e.target.value)}
            >
              <option value="">Default</option>
              {ollamaModels.map((m) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
            </DsoSelect>
          )}
          {llmProvider === "ollama" && ollamaStatus?.configured && ollamaModels.length === 0 && (
            <p className="text-xs text-muted">No Ollama models found. Make sure Ollama is running.</p>
          )}
        </div>
      )}
    </div>
  );
}
