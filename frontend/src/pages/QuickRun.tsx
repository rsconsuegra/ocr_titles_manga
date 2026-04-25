import { useEffect, useRef, useState } from "react";

import { getOCRModels } from "../api/ocr";
import { listProfiles } from "../api/profiles";
import { quickRun } from "../api/run";
import { getPreprocessSteps } from "../api/preprocess";
import type { ModelDescriptorResponse, ProfileResponse, QuickRunResponse, StepDescriptor } from "../api/types";
import { DsoButton, DsoCard, DsoErrorBanner, DsoSelect } from "../components/dso";
import ConfidenceMeter from "../components/ConfidenceMeter";
import PreprocessStepCard from "../components/PreprocessStepCard";
import { useFileReader } from "../hooks/useFileReader";
import { useYamlConfig } from "../hooks/useYamlConfig";

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
  const [result, setResult] = useState<QuickRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const ppYamlRef = useRef<HTMLInputElement>(null);
  const ocrYamlRef = useRef<HTMLInputElement>(null);
  const readFile = useFileReader();
  const parseYaml = useYamlConfig();

  useEffect(() => {
    getPreprocessSteps().then(setPreprocessSteps).catch(() => {});
    getOCRModels().then(setOcrModels).catch(() => {});
    listProfiles().then((res) => setProfiles(res.items)).catch(() => {});
  }, []);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const dataUrl = await readFile(file);
    setImageDataUrl(dataUrl);
    setImageFile(file);
    setResult(null);
  }

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
      const newConfig: Record<string, Record<string, unknown>> = {};
      const newEnabled: Record<string, boolean> = {};
      for (const [stepName, cfg] of Object.entries(profile.preprocess_steps)) {
        const enabled = (cfg as Record<string, unknown>).enabled === true;
        newEnabled[stepName] = enabled;
        const params = { ...cfg } as Record<string, unknown>;
        delete params.enabled;
        newConfig[stepName] = params as Record<string, unknown>;
      }
      setPreprocessConfig(newConfig);
      setPreprocessEnabled(newEnabled);
    }
    if (profile.ocr_models) {
      setUseCustomOcr(true);
      const newConfig: Record<string, Record<string, unknown>> = {};
      const newEnabled: Record<string, boolean> = {};
      for (const [modelName, cfg] of Object.entries(profile.ocr_models)) {
        const enabled = (cfg as Record<string, unknown>).enabled === true;
        newEnabled[modelName] = enabled;
        const params = { ...cfg } as Record<string, unknown>;
        delete params.enabled;
        newConfig[modelName] = params as Record<string, unknown>;
      }
      setOcrConfig(newConfig);
      setOcrEnabled(newEnabled);
    }
    setEnableLlm(profile.enable_llm);
  }

  function buildPreprocessSteps(): Record<string, Record<string, unknown>> | undefined {
    if (!useCustomPreprocess) return undefined;
    const ppSteps: Record<string, Record<string, unknown>> = {};
    for (const step of preprocessSteps) {
      const enabled = preprocessEnabled[step.name] ?? false;
      if (enabled) {
        ppSteps[step.name] = { ...preprocessConfig[step.name], enabled: true };
      }
    }
    return ppSteps;
  }

  function buildOcrModelsConfig(): Record<string, Record<string, unknown>> | undefined {
    if (!useCustomOcr) return undefined;
    const ocrModelsConfig: Record<string, Record<string, unknown>> = {};
    for (const m of ocrModels) {
      const enabled = ocrEnabled[m.name] ?? false;
      if (enabled) {
        ocrModelsConfig[m.name] = { ...ocrConfig[m.name], enabled: true };
      }
    }
    return ocrModelsConfig;
  }

  async function handleRun() {
    if (!imageFile) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await quickRun(imageFile, {
        preprocessSteps: buildPreprocessSteps(),
        ocrModels: buildOcrModelsConfig(),
        enableLlm,
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
          <div>
            <p className="tech-label mb-1">Image</p>
            <input ref={fileRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            <DsoButton
              variant="secondary"
              onClick={() => fileRef.current?.click()}
            >
              {imageDataUrl ? "Change Image" : "Upload Image"}
            </DsoButton>
            {imageDataUrl && (
              <img src={imageDataUrl} alt="Preview" className="mt-2 max-h-48 rounded border border-highlight/20" />
            )}
          </div>

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
                  <div key={m.name} className="neo-inset rounded-lg p-3">
                    <label className="flex items-center gap-2 text-sm font-medium text-bright">
                      <input type="checkbox" checked={ocrEnabled[m.name] ?? false} onChange={(e) => setOcrEnabled((prev) => ({ ...prev, [m.name]: e.target.checked }))} className={cbx} />
                      {m.label}
                      {!m.available && <span className="text-xs text-muted">(not available)</span>}
                    </label>
                    {ocrEnabled[m.name] && m.params.length > 0 && (
                      <div className="mt-2">
                        <PreprocessStepCard
                          step={{ name: m.name, label: m.label, description: m.description, params: m.params }}
                          params={ocrConfig[m.name] || {}}
                          enabled={true}
                          onParamsChange={(c) => setOcrConfig((prev) => ({ ...prev, [m.name]: c }))}
                          onEnabledChange={() => {}}
                          showEnabled={false}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </DsoCard>

          <label className="flex items-center gap-2 text-sm text-bright">
            <input type="checkbox" checked={enableLlm} onChange={(e) => setEnableLlm(e.target.checked)} className={cbx} />
            Post-process with LLM
          </label>

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
                <DsoCard key={i}>
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-bright">{ocr.model_name}</h3>
                    <ConfidenceMeter value={ocr.confidence} />
                  </div>
                  <div className="text-xs text-muted mb-2">{ocr.processing_time_ms}ms</div>
                  <div className="rounded bg-lcd p-3">
                    <pre className="whitespace-pre-wrap break-words text-sm text-bright/80">
                      {ocr.raw_text || "(empty)"}
                    </pre>
                  </div>
                  {ocr.error && (
                    <DsoErrorBanner className="mt-2">{ocr.error}</DsoErrorBanner>
                  )}
                </DsoCard>
              ))}

              {result.llm && (
                <DsoCard variant="lcd">
                  <h3 className="mb-2 text-sm font-semibold text-teal">LLM Extraction</h3>
                  <div className="space-y-1 text-sm">
                    {result.llm.title_en && (
                      <div>
                        <span className="text-muted">Title (EN):</span>{" "}
                        <span className="font-medium text-bright">{result.llm.title_en}</span>
                      </div>
                    )}
                    {result.llm.title_ja && (
                      <div>
                        <span className="text-muted">Title (JA):</span>{" "}
                        <span className="font-medium text-bright">{result.llm.title_ja}</span>
                      </div>
                    )}
                    {result.llm.code && (
                      <div>
                        <span className="text-muted">Code:</span>{" "}
                        <span className="font-mono text-bright">{result.llm.code}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-muted">Confidence:</span>
                      <ConfidenceMeter value={result.llm.confidence} />
                    </div>
                  </div>
                </DsoCard>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
