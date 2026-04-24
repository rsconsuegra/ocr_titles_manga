import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getOCRModels } from "../api/ocr";
import { getPreprocessSteps } from "../api/preprocess";
import {
  createProfile,
  getProfile,
  updateProfile,
} from "../api/profiles";
import type { ModelDescriptorResponse, StepDescriptor } from "../api/types";
import { DsoButton, DsoCard, DsoErrorBanner, DsoInput } from "../components/dso";
import PreprocessStepCard from "../components/PreprocessStepCard";

export default function ProfileEditor() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isDefault, setIsDefault] = useState(false);
  const [enableLlm, setEnableLlm] = useState(false);

  const [preprocessSteps, setPreprocessSteps] = useState<StepDescriptor[]>([]);
  const [preprocessConfig, setPreprocessConfig] = useState<Record<string, Record<string, unknown>>>({});
  const [preprocessEnabled, setPreprocessEnabled] = useState<Record<string, boolean>>({});

  const [ocrModels, setOcrModels] = useState<ModelDescriptorResponse[]>([]);
  const [ocrConfig, setOcrConfig] = useState<Record<string, Record<string, unknown>>>({});
  const [ocrEnabled, setOcrEnabled] = useState<Record<string, boolean>>({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pageLoading, setPageLoading] = useState(true);

  useEffect(() => {
    Promise.all([getPreprocessSteps(), getOCRModels()])
      .then(([steps, models]) => {
        setPreprocessSteps(steps);
        setOcrModels(models);
      })
      .catch(() => {});
  }, []);

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
        if (p.preprocess_steps) {
          for (const [stepName, cfg] of Object.entries(p.preprocess_steps)) {
            const enabled = (cfg as Record<string, unknown>).enabled === true;
            setPreprocessEnabled((prev) => ({ ...prev, [stepName]: enabled }));
            const params = { ...cfg } as Record<string, unknown>;
            delete params.enabled;
            setPreprocessConfig((prev) => ({ ...prev, [stepName]: params as Record<string, unknown> }));
          }
        }
        if (p.ocr_models) {
          for (const [modelName, cfg] of Object.entries(p.ocr_models)) {
            const enabled = (cfg as Record<string, unknown>).enabled === true;
            setOcrEnabled((prev) => ({ ...prev, [modelName]: enabled }));
            const params = { ...cfg } as Record<string, unknown>;
            delete params.enabled;
            setOcrConfig((prev) => ({ ...prev, [modelName]: params as Record<string, unknown> }));
          }
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setPageLoading(false));
  }, [id, isEdit]);

  async function handleSave() {
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setLoading(true);
    setError(null);

    const ppSteps: Record<string, Record<string, unknown>> = {};
    for (const step of preprocessSteps) {
      const enabled = preprocessEnabled[step.name] ?? false;
      ppSteps[step.name] = { ...preprocessConfig[step.name], enabled };
    }

    const ocrModelsData: Record<string, Record<string, unknown>> = {};
    for (const m of ocrModels) {
      const enabled = ocrEnabled[m.name] ?? false;
      ocrModelsData[m.name] = { ...ocrConfig[m.name], enabled };
    }

    try {
      if (isEdit && id) {
        await updateProfile(id, {
          name: name.trim(),
          description: description.trim() || null,
          preprocess_steps: ppSteps,
          ocr_models: ocrModelsData,
          enable_llm: enableLlm,
          is_default: isDefault,
        });
      } else {
        await createProfile({
          name: name.trim(),
          description: description.trim() || undefined,
          preprocess_steps: ppSteps,
          ocr_models: ocrModelsData,
          enable_llm: enableLlm,
          is_default: isDefault,
        });
      }
      navigate("/profiles");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setLoading(false);
    }
  }

  if (pageLoading) return <p className="tech-label breathing">Loading...</p>;

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-6 font-display text-xl font-bold text-bright">
        {isEdit ? "Edit Profile" : "New Profile"}
      </h1>

      {error && <DsoErrorBanner className="mb-4">{error}</DsoErrorBanner>}

      <div className="space-y-4">
        <DsoInput
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Manga Scan v2"
        />

        <DsoInput
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
        />

        <DsoCard>
          <h2 className="mb-3 tech-label-bright">Preprocessing Steps</h2>
          <div className="space-y-3">
            {preprocessSteps.map((step) => (
              <PreprocessStepCard
                key={step.name}
                step={step}
                params={preprocessConfig[step.name] || {}}
                enabled={preprocessEnabled[step.name] ?? false}
                onParamsChange={(c) =>
                  setPreprocessConfig((prev) => ({ ...prev, [step.name]: c }))
                }
                onEnabledChange={(v) =>
                  setPreprocessEnabled((prev) => ({ ...prev, [step.name]: v }))
                }
                showEnabled={true}
              />
            ))}
          </div>
        </DsoCard>

        <DsoCard>
          <h2 className="mb-3 tech-label-bright">OCR Models</h2>
          <div className="space-y-3">
            {ocrModels.map((m) => (
              <div key={m.name} className="neo-inset rounded-lg p-3">
                <label className="flex items-center gap-2 text-sm font-medium text-bright">
                  <input
                    type="checkbox"
                    checked={ocrEnabled[m.name] ?? false}
                    onChange={(e) =>
                      setOcrEnabled((prev) => ({ ...prev, [m.name]: e.target.checked }))
                    }
                    className="rounded border-highlight/40 bg-inset accent-teal"
                  />
                  {m.label}
                  {!m.available && (
                    <span className="text-xs text-muted">(not available)</span>
                  )}
                </label>
                {ocrEnabled[m.name] && m.params.length > 0 && (
                  <div className="mt-2">
                    <PreprocessStepCard
                      step={{
                        name: m.name,
                        label: m.label,
                        description: m.description,
                        params: m.params,
                      }}
                      params={ocrConfig[m.name] || {}}
                      enabled={true}
                      onParamsChange={(c) =>
                        setOcrConfig((prev) => ({ ...prev, [m.name]: c }))
                      }
                      onEnabledChange={() => {}}
                      showEnabled={false}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </DsoCard>

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-bright">
            <input
              type="checkbox"
              checked={enableLlm}
              onChange={(e) => setEnableLlm(e.target.checked)}
              className="rounded border-highlight/40 bg-inset accent-teal"
            />
            Enable LLM post-processing
          </label>
          <label className="flex items-center gap-2 text-sm text-bright">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
              className="rounded border-highlight/40 bg-inset accent-teal"
            />
            Set as default profile
          </label>
        </div>

        <div className="flex items-center gap-3">
          <DsoButton onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : isEdit ? "Update Profile" : "Create Profile"}
          </DsoButton>
          <DsoButton variant="secondary" onClick={() => navigate("/profiles")}>
            Cancel
          </DsoButton>
        </div>
      </div>
    </div>
  );
}
