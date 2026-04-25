import { useCallback, useEffect, useRef, useState } from "react";

import { exportPipeline, getPreprocessSteps, previewStep, previewPipeline } from "../api/preprocess";
import type { PipelineStepResult, StepDescriptor } from "../api/types";
import { DsoButton, DsoSelect } from "../components/dso";
import ImageCompare from "../components/ImageCompare";
import PipelineFilmstrip from "../components/PipelineFilmstrip";
import PreprocessStepCard from "../components/PreprocessStepCard";

type Tab = "step" | "pipeline";

export default function PreprocessPlayground() {
  const [steps, setSteps] = useState<StepDescriptor[]>([]);
  const [sourceImage, setSourceImage] = useState<string | null>(null);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [sourceFileName, setSourceFileName] = useState<string>("");
  const [tab, setTab] = useState<Tab>("step");

  const [selectedStep, setSelectedStep] = useState<string>("grayscale");
  const [stepParams, setStepParams] = useState<Record<string, unknown>>({});
  const [stepResult, setStepResult] = useState<{ image: string; metadata: Record<string, unknown>; time_ms: number } | null>(null);
  const [stepLoading, setStepLoading] = useState(false);

  const [pipelineConfigs, setPipelineConfigs] = useState<Record<string, Record<string, unknown>>>({});
  const [pipelineEnabled, setPipelineEnabled] = useState<Record<string, boolean>>({});
  const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[] | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getPreprocessSteps().then((s) => {
      setSteps(s);
      if (s.length > 0 && s[0]) setSelectedStep(s[0].name);
    });
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSourceFileName(file.name);
    setSourceFile(file);
    const reader = new FileReader();
    reader.onload = () => setSourceImage(reader.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handlePaste = useCallback(() => {
    navigator.clipboard.read().then(async (items) => {
      for (const item of items) {
        const imageType = item.types?.find((t) => t.startsWith("image/"));
        if (imageType) {
          const blob = await item.getType(imageType);
          const file = new File([blob], "pasted.png", { type: imageType });
          setSourceFile(file);
          setSourceFileName("pasted.png");
          const reader = new FileReader();
          reader.onload = () => setSourceImage(reader.result as string);
          reader.readAsDataURL(blob);
          return;
        }
      }
    }).catch(() => {});
  }, []);

  const handlePreviewStep = useCallback(async () => {
    if (!sourceFile) return;
    setStepLoading(true);
    try {
      const res = await previewStep(sourceFile, selectedStep, stepParams);
      setStepResult({ image: res.image, metadata: res.metadata, time_ms: res.processing_time_ms });
    } catch {
      setStepResult(null);
    } finally {
      setStepLoading(false);
    }
  }, [sourceFile, selectedStep, stepParams]);

  const handlePreviewPipeline = useCallback(async () => {
    if (!sourceFile) return;
    setPipelineLoading(true);
    try {
      const merged: Record<string, Record<string, unknown>> = {};
      for (const step of steps) {
        const enabled = pipelineEnabled[step.name] ?? true;
        const params = { ...pipelineConfigs[step.name] };
        params["enabled"] = enabled;
        merged[step.name] = params;
      }
      const res = await previewPipeline(sourceFile, merged);
      setPipelineResults(res.steps);
    } catch {
      setPipelineResults(null);
    } finally {
      setPipelineLoading(false);
    }
  }, [sourceFile, steps, pipelineConfigs, pipelineEnabled]);

  const handleExport = useCallback(async () => {
    const merged: Record<string, Record<string, unknown>> = {};
    for (const step of steps) {
      merged[step.name] = { ...pipelineConfigs[step.name], enabled: pipelineEnabled[step.name] ?? true };
    }
    const res = await exportPipeline(merged);
    const blob = new Blob([res.yaml], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "preprocess.yaml";
    a.click();
    URL.revokeObjectURL(url);
  }, [steps, pipelineConfigs, pipelineEnabled]);

  const currentStep = steps.find((s) => s.name === selectedStep);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">Preprocessing Playground</h1>
        <DsoButton variant="secondary" onClick={handleExport}>
          Export YAML
        </DsoButton>
      </div>

      <div className="flex items-center gap-3">
        <input ref={fileRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
        <DsoButton onClick={() => fileRef.current?.click()}>Upload Image</DsoButton>
        <DsoButton variant="secondary" onClick={handlePaste}>Paste</DsoButton>
        {sourceFileName && <span className="text-sm text-muted">{sourceFileName}</span>}
      </div>

      {sourceImage && (
        <div className="w-48 neo-deep-inset overflow-hidden rounded">
          <img src={sourceImage} alt="Source" className="block w-full" />
          <div className="tech-label bg-panel-light/50 px-2 py-1">Source</div>
        </div>
      )}

      <div className="flex gap-1 border-b border-highlight/20">
        {(["step", "pipeline"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={[
              "px-4 py-2 text-sm font-medium capitalize transition-colors",
              tab === t
                ? "border-b-2 border-teal text-teal"
                : "text-muted hover:text-bright",
            ].join(" ")}
          >
            {t === "step" ? "Single Step" : "Full Pipeline"}
          </button>
        ))}
      </div>

      {tab === "step" && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <DsoSelect
              label="Step"
              value={selectedStep}
              onChange={(e) => {
                setSelectedStep(e.target.value);
                setStepParams({});
                setStepResult(null);
              }}
            >
              {steps.map((s) => (
                <option key={s.name} value={s.name}>{s.label}</option>
              ))}
            </DsoSelect>
            {currentStep && currentStep.params.length > 0 && (
              <PreprocessStepCard
                step={currentStep}
                params={stepParams}
                enabled={true}
                showEnabled={false}
                onParamsChange={setStepParams}
                onEnabledChange={() => {}}
              />
            )}
            <DsoButton
              onClick={handlePreviewStep}
              disabled={!sourceFile || stepLoading}
            >
              {stepLoading ? "Processing..." : "Preview Step"}
            </DsoButton>
          </div>

          <div>
            {stepResult && sourceImage && (
              <div className="space-y-3">
                <ImageCompare
                  beforeSrc={sourceImage}
                  afterSrc={stepResult.image}
                  beforeLabel="Original"
                  afterLabel={currentStep?.label || "Result"}
                />
                <div className="text-xs text-muted">
                  {stepResult.time_ms}ms &middot;{" "}
                  {Object.entries(stepResult.metadata)
                    .map(([k, v]) => `${k}: ${String(v)}`)
                    .join(" · ")}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "pipeline" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {steps.map((s) => (
              <PreprocessStepCard
                key={s.name}
                step={s}
                params={pipelineConfigs[s.name] || {}}
                enabled={pipelineEnabled[s.name] ?? true}
                onParamsChange={(p) =>
                  setPipelineConfigs((prev) => ({ ...prev, [s.name]: p }))
                }
                onEnabledChange={(e) =>
                  setPipelineEnabled((prev) => ({ ...prev, [s.name]: e }))
                }
              />
            ))}
          </div>
          <DsoButton
            onClick={handlePreviewPipeline}
            disabled={!sourceFile || pipelineLoading}
          >
            {pipelineLoading ? "Processing..." : "Preview Pipeline"}
          </DsoButton>

          {pipelineResults && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-bright">Pipeline Result</h3>
              <PipelineFilmstrip steps={pipelineResults} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
