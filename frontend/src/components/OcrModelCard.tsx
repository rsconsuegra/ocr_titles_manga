import type { ModelDescriptorResponse, OllamaModelInfo, OllamaStatusResponse } from "../api/types";
import OllamaModelSelector from "./OllamaModelSelector";
import PreprocessStepCard from "./PreprocessStepCard";

interface OcrModelCardProps {
  model: ModelDescriptorResponse;
  enabled: boolean;
  config: Record<string, unknown>;
  onEnabledChange: (checked: boolean) => void;
  onConfigChange: (cfg: Record<string, unknown>) => void;
  ollamaStatus?: OllamaStatusResponse | null;
  ollamaModels?: OllamaModelInfo[];
  visionModelValue?: string;
  onVisionModelChange?: (value: string) => void;
}

const CBX = "rounded border-linen bg-linen accent-indigo";

export default function OcrModelCard({
  model,
  enabled,
  config,
  onEnabledChange,
  onConfigChange,
  ollamaStatus,
  ollamaModels,
  visionModelValue,
  onVisionModelChange,
}: OcrModelCardProps) {
  return (
    <div className="rounded-lg border border-linen bg-cream p-3">
      <label className="flex items-center gap-2 text-sm font-medium text-charcoal">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
          className={CBX}
        />
        {model.label}
        {!model.available && <span className="text-xs text-sand">(not available)</span>}
      </label>
      {enabled && model.params.length > 0 && (
        <div className="mt-2">
          <PreprocessStepCard
            step={{
              name: model.name,
              label: model.label,
              description: model.description,
              params: model.params,
            }}
            params={config}
            enabled={true}
            onParamsChange={onConfigChange}
            onEnabledChange={() => {}}
            showEnabled={false}
          />
        </div>
      )}
      {model.name === "ollama_vision" && enabled && ollamaStatus?.configured && (
        <div className="mt-2">
          <OllamaModelSelector
            label="Ollama Vision Model"
            models={ollamaModels ?? []}
            value={visionModelValue ?? ""}
            onChange={onVisionModelChange ?? (() => {})}
            emptyMessage="No Ollama vision models found. Pull a vision model first."
          />
        </div>
      )}
    </div>
  );
}
