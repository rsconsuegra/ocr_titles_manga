import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getOpenRouterModels } from "../api/llm";
import { getOCRModels } from "../api/ocr";
import { getPreprocessSteps } from "../api/preprocess";
import { createProfile, getProfile, updateProfile } from "../api/profiles";
import type { ModelDescriptorResponse, OpenRouterModel, StepDescriptor } from "../api/types";
import LlmConfigSection from "../components/LlmConfigSection";
import OcrModelCard from "../components/OcrModelCard";
import OllamaModelSelector from "../components/OllamaModelSelector";
import PreprocessStepCard from "../components/PreprocessStepCard";
import PromptSettingsPanel from "../components/PromptSettingsPanel";
import { Button, Card, ErrorBanner, FormSkeleton, Input } from "../components/ui";
import { useLlmPromptState } from "../hooks/useLlmPromptState";
import { useOllamaModels } from "../hooks/useOllamaModels";
import { parseStepEntries } from "../utils/configParsing";

export default function ProfileEditor() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [enableLlm, setEnableLlm] = useState(false);
  const [llmProvider, setLlmProvider] = useState("openrouter");
  const [ollamaDefaultModel, setOllamaDefaultModel] = useState("");
  const promptState = useLlmPromptState({ userPromptTemplate: "{ocr_text}" });
  const { llmModels: ollamaModels, status: ollamaStatus } = useOllamaModels();
  const [openRouterModels, setOpenRouterModels] = useState<OpenRouterModel[]>([]);

  const [preprocessSteps, setPreprocessSteps] = useState<StepDescriptor[]>([]);
  const [preprocessConfig, setPreprocessConfig] = useState<Record<string, Record<string, unknown>>>(
    {},
  );
  const [preprocessEnabled, setPreprocessEnabled] = useState<Record<string, boolean>>({});

  const [ocrModels, setOcrModels] = useState<ModelDescriptorResponse[]>([]);
  const [ocrConfig, setOcrConfig] = useState<Record<string, Record<string, unknown>>>({});
  const [ocrEnabled, setOcrEnabled] = useState<Record<string, boolean>>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPreprocessSteps(), getOCRModels(), getOpenRouterModels()])
      .then(([steps, models, orModels]) => {
        setPreprocessSteps(steps);
        setOcrModels(models);
        setOpenRouterModels(orModels);
      })
      .catch(() => {});
  }, []);

  /* eslint-disable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps -- data-fetching; promptState is stable */
  useEffect(() => {
    if (!isEdit || !id) {
      setPageLoading(false);
      return;
    }
    getProfile(id)
      .then((p) => {
        setName(p.name);
        setDescription(p.description || "");
        setIsDefault(p.is_default);
        setEnableLlm(p.enable_llm);
        setLlmProvider(p.llm_provider || "openrouter");
        promptState.loadFromProfile(p);
        if (p.preprocess_steps) {
          const { config, enabled } = parseStepEntries(p.preprocess_steps);
          setPreprocessConfig(config);
          setPreprocessEnabled(enabled);
        }
        if (p.ocr_models) {
          const { config, enabled } = parseStepEntries(p.ocr_models);
          setOcrConfig(config);
          setOcrEnabled(enabled);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setPageLoading(false));
  }, [id, isEdit]);
  /* eslint-enable react-hooks/set-state-in-effect, react-hooks/exhaustive-deps */

  function buildPreprocessPayload(): Record<string, Record<string, unknown>> {
    const ppSteps: Record<string, Record<string, unknown>> = {};
    for (const step of preprocessSteps) {
      const enabled = preprocessEnabled[step.name] ?? false;
      ppSteps[step.name] = { ...preprocessConfig[step.name], enabled };
    }
    return ppSteps;
  }

  function buildOcrPayload(): Record<string, Record<string, unknown>> {
    const ocrModelsData: Record<string, Record<string, unknown>> = {};
    for (const m of ocrModels) {
      const enabled = ocrEnabled[m.name] ?? false;
      ocrModelsData[m.name] = { ...ocrConfig[m.name], enabled };
    }
    return ocrModelsData;
  }

  async function handleSave() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    setError(null);

    const payload = {
      name: name.trim(),
      description: description.trim() || undefined,
      preprocess_steps: buildPreprocessPayload(),
      ocr_models: buildOcrPayload(),
      enable_llm: enableLlm,
      llm_provider: llmProvider,
      llm_config: promptState.toConfig(),
      is_default: isDefault,
    };

    try {
      if (isEdit && id) {
        await updateProfile(id, { ...payload, description: description.trim() || null });
      } else {
        await createProfile(payload);
      }
      navigate("/profiles");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  if (pageLoading) return <FormSkeleton />;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 font-display text-xl font-bold text-ink">
        {isEdit ? "Edit Profile" : "New Profile"}
      </h1>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      <div className="space-y-4">
        <Card>
          <Input
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Manga Scan v2"
          />
          <Input
            label="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            className="mt-3"
          />
        </Card>

        <Card>
          <h2 className="mb-3 label-text text-charcoal">Preprocessing Steps</h2>
          <div className="space-y-3">
            {preprocessSteps.map((step) => (
              <PreprocessStepCard
                key={step.name}
                step={step}
                params={preprocessConfig[step.name] || {}}
                enabled={preprocessEnabled[step.name] ?? false}
                onParamsChange={(c) => setPreprocessConfig((prev) => ({ ...prev, [step.name]: c }))}
                onEnabledChange={(v) =>
                  setPreprocessEnabled((prev) => ({ ...prev, [step.name]: v }))
                }
                showEnabled={true}
              />
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="mb-3 label-text text-charcoal">OCR Models</h2>
          <div className="space-y-3">
            {ocrModels.map((m) => (
              <OcrModelCard
                key={m.name}
                model={m}
                enabled={ocrEnabled[m.name] ?? false}
                config={ocrConfig[m.name] || {}}
                onEnabledChange={(checked) => {
                  setOcrEnabled((prev) => ({ ...prev, [m.name]: checked }));
                  if (m.name === "ollama_vision" && checked) setEnableLlm(false);
                }}
                onConfigChange={(c) => setOcrConfig((prev) => ({ ...prev, [m.name]: c }))}
              />
            ))}
          </div>
        </Card>

        <div className="space-y-3">
          <LlmConfigSection
            enableLlm={enableLlm}
            onEnableLlmChange={setEnableLlm}
            llmDisabled={!!ocrEnabled["ollama_vision"]}
            llmProvider={llmProvider}
            onLlmProviderChange={setLlmProvider}
            llmModel={ollamaDefaultModel}
            onLlmModelChange={setOllamaDefaultModel}
            ollamaModels={ollamaModels}
            ollamaStatus={ollamaStatus}
            openRouterModels={openRouterModels}
            openRouterModel={promptState.llmModel}
            onOpenRouterModelChange={promptState.setLlmModel}
            reasoningEnabled={promptState.reasoningEnabled}
            onReasoningEnabledChange={promptState.setReasoningEnabled}
            radioName="llm_provider_profile"
          />

          {enableLlm &&
            llmProvider === "ollama" &&
            ollamaStatus?.configured &&
            ollamaModels.length > 0 && (
              <OllamaModelSelector
                label="Default Ollama Model"
                models={ollamaModels}
                value={ollamaDefaultModel}
                onChange={setOllamaDefaultModel}
                showDetails
                emptyMessage="No models found. Make sure Ollama is running."
              />
            )}

          {enableLlm && (
            <Card>
              <p className="label-text text-charcoal mb-2">Prompt Settings</p>
              <PromptSettingsPanel
                systemPrompt={promptState.llmSystemPrompt}
                onSystemPromptChange={promptState.setLlmSystemPrompt}
                userPrompt={promptState.llmUserPrompt}
                onUserPromptChange={promptState.setLlmUserPrompt}
                temperature={promptState.llmTemperature}
                onTemperatureChange={promptState.setLlmTemperature}
                maxOcrChars={promptState.llmMaxOcrChars}
                onMaxOcrCharsChange={promptState.setLlmMaxOcrChars}
                showToggle={false}
                isOpen={true}
                onToggle={() => {}}
                size="md"
              />
            </Card>
          )}

          <label className="flex items-center gap-2 text-sm text-charcoal">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="rounded border-linen bg-cream accent-indigo"
            />
            Set as default profile
          </label>
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : isEdit ? "Update Profile" : "Create Profile"}
          </Button>
          <Button variant="ghost" onClick={() => navigate("/profiles")}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
