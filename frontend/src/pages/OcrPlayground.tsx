import { useEffect, useState } from "react";

import { getOpenRouterModels } from "../api/llm";
import { exportOCRConfig, getOCRModels, runOCR } from "../api/ocr";
import type { ModelDescriptorResponse, OCRRunResponse, OpenRouterModel } from "../api/types";
import LlmConfigSection from "../components/LlmConfigSection";
import LlmExtractionCard from "../components/LlmExtractionCard";
import OcrResultCard from "../components/OcrResultCard";
import OllamaModelSelector from "../components/OllamaModelSelector";
import PreprocessStepCard from "../components/PreprocessStepCard";
import PromptSettingsPanel from "../components/PromptSettingsPanel";
import SingleImageUpload from "../components/SingleImageUpload";
import { Button, ErrorBanner, FormSkeleton } from "../components/ui";
import { OLLAMA_VISION_MODEL } from "../constants";
import { useLlmPromptState } from "../hooks/useLlmPromptState";
import { useOllamaModels } from "../hooks/useOllamaModels";

export default function OcrPlayground() {
  const [models, setModels] = useState<ModelDescriptorResponse[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [imageDataUrl, setImageDataUrl] = useState<string>("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [params, setParams] = useState<Record<string, Record<string, unknown>>>({});
  const [enableLlm, setEnableLlm] = useState(false);
  const [llmProvider, setLlmProvider] = useState("openrouter");
  const [llmModel, setLlmModel] = useState("");
  const promptState = useLlmPromptState();
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);
  const [result, setResult] = useState<OCRRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { status: ollamaStatus, visionModels, llmModels: ollamaLlmModels } = useOllamaModels();

  useEffect(() => {
    getOCRModels()
      .then((data) => {
        setModels(data);
        const sel = data.find((m) => m.available && m.enabled);
        setSelectedModel(sel?.name || (data[0]?.name ?? ""));
      })
      .catch(() => setError("Failed to load OCR models"));
    getOpenRouterModels()
      .then(setOpenRouterModels)
      .catch(() => {});
  }, []);

  const currentModel = models.find((m) => m.name === selectedModel);

  if (models.length === 0 && !error) return <FormSkeleton />;

  async function handleRun() {
    if (!imageFile || !selectedModel) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const effectiveLlmModel = llmProvider === "openrouter" ? promptState.llmModel : llmModel;
      const resp = await runOCR(
        imageFile,
        selectedModel,
        params[selectedModel] || {},
        enableLlm,
        llmProvider,
        effectiveLlmModel,
        promptState.toConfig(),
      );
      setResult(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "OCR run failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    try {
      const exportModels: Record<string, Record<string, unknown>> = {};
      for (const m of models) {
        exportModels[m.name] = {
          enabled: m.enabled,
          ...(params[m.name] || {}),
        };
      }
      const { yaml } = await exportOCRConfig(exportModels);
      const blob = new Blob([yaml], { type: "text/yaml" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "ocrs.yaml";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-ink">OCR Playground</h1>
        <Button variant="secondary" onClick={handleExport}>
          Export Config
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <SingleImageUpload
            imageDataUrl={imageDataUrl}
            fileName={imageFile?.name ?? ""}
            onImageChange={(dataUrl, file) => {
              setImageDataUrl(dataUrl);
              setImageFile(file);
              setResult(null);
            }}
          />

          <div>
            <span className="label-text block mb-2">Model</span>
            <div className="grid grid-cols-1 gap-2">
              {models.map((m) => (
                <button
                  key={m.name}
                  onClick={() => {
                    setSelectedModel(m.name);
                    if (m.name === OLLAMA_VISION_MODEL) setEnableLlm(false);
                  }}
                  disabled={!m.available || !m.enabled}
                  className={`
                    flex items-center gap-3 rounded-lg border p-3 text-left transition-colors
                    ${
                      selectedModel === m.name
                        ? "border-indigo bg-indigo-pale/30"
                        : "border-linen bg-snow hover:border-indigo/30"
                    }
                    ${!m.available || !m.enabled ? "opacity-40 cursor-not-allowed" : ""}
                  `}
                >
                  <span
                    className={`size-4 shrink-0 rounded-full border-2 flex items-center justify-center ${
                      selectedModel === m.name ? "border-indigo" : "border-linen"
                    }`}
                  >
                    {selectedModel === m.name && <span className="size-2 rounded-full bg-indigo" />}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-charcoal">{m.label}</p>
                    {!m.available && <p className="text-xs text-sand">Not available</p>}
                    {!m.enabled && m.available && <p className="text-xs text-sand">Disabled</p>}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {currentModel && currentModel.params.length > 0 && (
            <PreprocessStepCard
              step={{
                name: currentModel.name,
                label: currentModel.label,
                description: currentModel.description,
                params: currentModel.params,
              }}
              params={params[selectedModel] || {}}
              enabled={true}
              onParamsChange={(c) => setParams((prev) => ({ ...prev, [selectedModel]: c }))}
              onEnabledChange={() => {}}
              showEnabled={false}
            />
          )}

          {selectedModel === OLLAMA_VISION_MODEL && ollamaStatus?.configured && (
            <OllamaModelSelector
              label="Ollama Vision Model"
              models={visionModels}
              value={(params[selectedModel]?.model_name as string) || ""}
              onChange={(v) =>
                setParams((prev) => ({
                  ...prev,
                  [selectedModel]: { ...prev[selectedModel], model_name: v },
                }))
              }
              emptyMessage="No Ollama vision models found. Pull a vision model (e.g. llava, gemma3) first."
            />
          )}

          <LlmConfigSection
            enableLlm={enableLlm}
            onEnableLlmChange={setEnableLlm}
            llmDisabled={selectedModel === OLLAMA_VISION_MODEL}
            llmProvider={llmProvider}
            onLlmProviderChange={setLlmProvider}
            llmModel={llmModel}
            onLlmModelChange={setLlmModel}
            ollamaModels={ollamaLlmModels}
            ollamaStatus={ollamaStatus}
            openRouterModels={openRouterModels}
            openRouterModel={promptState.llmModel}
            onOpenRouterModelChange={promptState.setLlmModel}
            reasoningEnabled={promptState.reasoningEnabled}
            onReasoningEnabledChange={promptState.setReasoningEnabled}
            radioName="llm_provider_ocr"
          />

          {enableLlm && (
            <PromptSettingsPanel
              systemPrompt={promptState.llmSystemPrompt}
              onSystemPromptChange={promptState.setLlmSystemPrompt}
              userPrompt={promptState.llmUserPrompt}
              onUserPromptChange={promptState.setLlmUserPrompt}
              temperature={promptState.llmTemperature}
              onTemperatureChange={promptState.setLlmTemperature}
              maxOcrChars={promptState.llmMaxOcrChars}
              onMaxOcrCharsChange={promptState.setLlmMaxOcrChars}
              showToggle={true}
              isOpen={promptState.showPromptSettings}
              onToggle={() => promptState.setShowPromptSettings(!promptState.showPromptSettings)}
              size="sm"
            />
          )}

          <Button
            onClick={handleRun}
            disabled={loading || !imageFile || !selectedModel}
            className="w-full"
          >
            {loading ? "Running OCR..." : "Run OCR"}
          </Button>
        </div>

        <div className="space-y-4">
          {error && <ErrorBanner message={error} />}

          {result && (
            <>
              <OcrResultCard
                modelName={result.ocr.model_name}
                processingTimeMs={result.ocr.processing_time_ms}
                confidence={result.ocr.confidence}
                rawText={result.ocr.raw_text}
                error={result.ocr.error}
                blocks={result.ocr.blocks}
                imageDataUrl={imageDataUrl}
                variant="full"
              />

              {result.llm && (
                <LlmExtractionCard
                  titleEn={result.llm.title_en}
                  titleJa={result.llm.title_ja}
                  code={result.llm.code}
                  confidence={result.llm.confidence}
                  method={result.llm.source_method}
                  rawResponse={result.llm.raw_response}
                  extraMetadata={result.llm.extra_metadata}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
