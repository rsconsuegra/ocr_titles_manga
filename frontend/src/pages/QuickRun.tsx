import { useEffect, useRef, useState } from "react";

import { getOpenRouterModels } from "../api/llm";
import { getOCRModels } from "../api/ocr";
import { getPreprocessSteps } from "../api/preprocess";
import { listProfiles } from "../api/profiles";
import { quickRun } from "../api/run";
import type { ModelDescriptorResponse, OpenRouterModel, ProfileResponse, QuickRunResponse, StepDescriptor } from "../api/types";
import { DsoButton, DsoCard, DsoErrorBanner, DsoSelect } from "../components/dso";
import LlmConfigSection from "../components/LlmConfigSection";
import LlmExtractionCard from "../components/LlmExtractionCard";
import OcrModelCard from "../components/OcrModelCard";
import OcrResultCard from "../components/OcrResultCard";
import PreprocessStepCard from "../components/PreprocessStepCard";
import PromptSettingsPanel from "../components/PromptSettingsPanel";
import SingleImageUpload from "../components/SingleImageUpload";
import { OLLAMA_VISION_MODEL } from "../constants";
import { useLlmPromptState } from "../hooks/useLlmPromptState";
import { useOllamaModels } from "../hooks/useOllamaModels";
import { useYamlConfig } from "../hooks/useYamlConfig";
import { parseStepEntries } from "../utils/configParsing";

export default function QuickRun() {
  const [preprocessSteps, setPreprocessSteps] = useState<StepDescriptor[]>([]);
  const [ocrModels, setOcrModels] = useState<ModelDescriptorResponse[]>([]);
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [imageDataUrl, setImageDataUrl] = useState<string>("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [useCustomPreprocess, setUseCustomPreprocess] = useState(false);
  const [useCustomOcr, setUseCustomOcr] = useState(false);
  const [preprocessConfig, setPreprocessConfig] = useState<Record<string, Record<string, unknown>>>({});
  const [preprocessEnabled, setPreprocessEnabled] = useState<Record<string, boolean>>({});
  const [ocrConfig, setOcrConfig] = useState<Record<string, Record<string, unknown>>>({});
  const [ocrEnabled, setOcrEnabled] = useState<Record<string, boolean>>({});
  const [enableLlm, setEnableLlm] = useState(false);
  const [llmProvider, setLlmProvider] = useState("openrouter");
  const [llmModel, setLlmModel] = useState("");
  const promptState = useLlmPromptState();
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);
  const [result, setResult] = useState<QuickRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { status: ollamaStatus, visionModels, llmModels: ollamaLlmModels } = useOllamaModels();
  const ppYamlRef = useRef<HTMLInputElement>(null);
  const ocrYamlRef = useRef<HTMLInputElement>(null);
  const parseYaml = useYamlConfig();

  useEffect(() => {
    getPreprocessSteps().then(setPreprocessSteps).catch(() => {});
    getOCRModels().then(setOcrModels).catch(() => {});
    listProfiles().then((res) => setProfiles(res.items)).catch(() => {});
    getOpenRouterModels().then(setOpenRouterModels).catch(() => {});
  }, []);

  function handlePreprocessYamlUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const { config, enabled } = parseYaml(reader.result as string, "preprocessing");
        setPreprocessConfig(config);
        setPreprocessEnabled(enabled);
      } catch (e) {
        setError(e instanceof Error ? `Invalid YAML: ${e.message}` : "Failed to parse YAML");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function handleOcrYamlUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const { config, enabled } = parseYaml(reader.result as string, "models");
        setOcrConfig(config);
        setOcrEnabled(enabled);
      } catch (e) {
        setError(e instanceof Error ? `Invalid YAML: ${e.message}` : "Failed to parse YAML");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  }

  function handleLoadProfile(profileId: string) {
    setSelectedProfileId(profileId);
    if (!profileId) return;
    const profile = profiles.find((p) => p.id === profileId);
    if (!profile) return;
    if (profile.preprocess_steps) {
      setUseCustomPreprocess(true);
      const { config, enabled } = parseStepEntries(profile.preprocess_steps);
      setPreprocessConfig(config);
      setPreprocessEnabled(enabled);
    }
    if (profile.ocr_models) {
      setUseCustomOcr(true);
      const { config, enabled } = parseStepEntries(profile.ocr_models);
      setOcrConfig(config);
      setOcrEnabled(enabled);
    }
    setEnableLlm(profile.enable_llm);
    setLlmProvider(profile.llm_provider || "openrouter");
    promptState.loadFromProfile(profile);
  }

  async function handleRun() {
    if (!imageFile) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let finalPpSteps: Record<string, Record<string, unknown>> | undefined;
      if (useCustomPreprocess) {
        finalPpSteps = {};
        for (const step of preprocessSteps) {
          const enabled = preprocessEnabled[step.name] ?? false;
          if (enabled) {
            finalPpSteps[step.name] = { ...preprocessConfig[step.name], enabled: true };
          }
        }
      }

      let finalOcrModels: Record<string, Record<string, unknown>> | undefined;
      if (useCustomOcr) {
        finalOcrModels = {};
        for (const m of ocrModels) {
          const enabled = ocrEnabled[m.name] ?? false;
          if (enabled) {
            finalOcrModels[m.name] = { ...ocrConfig[m.name], enabled: true };
          }
        }
      }

      const effectiveLlmModel = llmProvider === "openrouter"
        ? promptState.llmModel
        : llmModel;
      const resp = await quickRun(imageFile, {
        preprocessSteps: finalPpSteps,
        ocrModels: finalOcrModels,
        enableLlm,
        llmProvider,
        llmModel: effectiveLlmModel || undefined,
        llmConfig: promptState.toConfig(),
        profileId: selectedProfileId || undefined,
      });
      setResult(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quick run failed");
    } finally {
      setLoading(false);
    }
  }

  const cbx = "rounded border-highlight/40 bg-inset accent-teal";

  return (
    <div>
      <h1 className="mb-6 font-display text-xl font-bold text-bright">Quick Run</h1>

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

          {profiles.length > 0 && (
            <DsoSelect
              label="Load Profile"
              value={selectedProfileId}
              onChange={(e) => handleLoadProfile(e.target.value)}
            >
              <option value="">No profile</option>
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}{p.is_default ? " (default)" : ""}
                </option>
              ))}
            </DsoSelect>
          )}

          <DsoCard>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm font-medium text-bright">
                <input type="checkbox" checked={useCustomPreprocess} onChange={(e) => setUseCustomPreprocess(e.target.checked)} className={cbx} />
                Custom Preprocessing
              </label>
              {useCustomPreprocess && (
                <>
                  <input ref={ppYamlRef} type="file" accept=".yaml,.yml" onChange={handlePreprocessYamlUpload} className="hidden" />
                  <DsoButton variant="ghost" className="text-xs px-2 py-1" onClick={() => ppYamlRef.current?.click()}>
                    Upload YAML
                  </DsoButton>
                </>
              )}
            </div>
            {useCustomPreprocess && (
              <div className="mt-3 space-y-3">
                {preprocessSteps.map((step) => (
                  <PreprocessStepCard
                    key={step.name}
                    step={step}
                    params={preprocessConfig[step.name] || {}}
                    enabled={preprocessEnabled[step.name] ?? false}
                    onParamsChange={(c) => setPreprocessConfig((prev) => ({ ...prev, [step.name]: c }))}
                    onEnabledChange={(v) => setPreprocessEnabled((prev) => ({ ...prev, [step.name]: v }))}
                    showEnabled={true}
                  />
                ))}
              </div>
            )}
          </DsoCard>

          <DsoCard>
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm font-medium text-bright">
                <input type="checkbox" checked={useCustomOcr} onChange={(e) => setUseCustomOcr(e.target.checked)} className={cbx} />
                Custom OCR Models
              </label>
              {useCustomOcr && (
                <>
                  <input ref={ocrYamlRef} type="file" accept=".yaml,.yml" onChange={handleOcrYamlUpload} className="hidden" />
                  <DsoButton variant="ghost" className="text-xs px-2 py-1" onClick={() => ocrYamlRef.current?.click()}>
                    Upload YAML
                  </DsoButton>
                </>
              )}
            </div>
            {useCustomOcr && (
              <div className="mt-3 space-y-3">
                {ocrModels.map((m) => (
                  <OcrModelCard
                    key={m.name}
                    model={m}
                    enabled={ocrEnabled[m.name] ?? false}
                    config={ocrConfig[m.name] || {}}
                    onEnabledChange={(checked) => {
                      setOcrEnabled((prev) => ({ ...prev, [m.name]: checked }));
                      if (m.name === OLLAMA_VISION_MODEL && checked) setEnableLlm(false);
                    }}
                    onConfigChange={(c) => setOcrConfig((prev) => ({ ...prev, [m.name]: c }))}
                    ollamaStatus={ollamaStatus}
                    ollamaModels={visionModels}
                    visionModelValue={(ocrConfig[m.name]?.model_name as string) || ""}
                    onVisionModelChange={(v) =>
                      setOcrConfig((prev) => ({
                        ...prev,
                        [m.name]: { ...prev[m.name], model_name: v },
                      }))
                    }
                  />
                ))}
              </div>
            )}
          </DsoCard>

          <LlmConfigSection
            enableLlm={enableLlm}
            onEnableLlmChange={setEnableLlm}
            llmDisabled={!!ocrEnabled[OLLAMA_VISION_MODEL]}
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
            radioName="llm_provider_quick"
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

          <DsoButton onClick={handleRun} disabled={loading || !imageFile} className="w-full">
            {loading ? "Running..." : "Run Pipeline"}
          </DsoButton>
        </div>

        <div className="space-y-4">
          {error && <DsoErrorBanner>{error}</DsoErrorBanner>}

          {result && (
            <>
              <div className="text-sm text-muted">
                Total time: {result.total_processing_time_ms}ms
              </div>

              {result.ocr_results.length === 0 && (
                <DsoCard variant="lcd">
                  <p className="text-amber">No OCR models were run. Enable custom OCR models to get results.</p>
                </DsoCard>
              )}

              {result.ocr_results.map((ocr, i) => (
                <OcrResultCard
                  key={i}
                  modelName={ocr.model_name}
                  processingTimeMs={ocr.processing_time_ms}
                  confidence={ocr.confidence}
                  rawText={ocr.raw_text}
                  error={ocr.error}
                  blocks={ocr.blocks}
                  imageDataUrl={imageDataUrl}
                  variant={ocr.blocks && ocr.blocks.length > 0 ? "full" : "compact"}
                />
              ))}

              {result.llm && (
                <LlmExtractionCard
                  titleEn={result.llm.title_en}
                  titleJa={result.llm.title_ja}
                  code={result.llm.code}
                  confidence={result.llm.confidence}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
