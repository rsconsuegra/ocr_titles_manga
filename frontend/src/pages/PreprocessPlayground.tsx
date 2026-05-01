import { Fragment, useCallback, useEffect, useState } from "react";

import {
  exportPipeline,
  getPreprocessSteps,
  previewPipeline,
  previewStep,
} from "../api/preprocess";
import type { PipelineStepResult, StepDescriptor } from "../api/types";
import ImageCompare from "../components/ImageCompare";
import PipelineFilmstrip from "../components/PipelineFilmstrip";
import PreprocessStepCard from "../components/PreprocessStepCard";
import SingleImageUpload from "../components/SingleImageUpload";
import { Button, FormSkeleton } from "../components/ui";

export default function PreprocessPlayground() {
  const [steps, setSteps] = useState<StepDescriptor[]>([]);
  const [sourceImage, setSourceImage] = useState<string>("");
  const [sourceFile, setSourceFile] = useState<File | null>(null);

  const [selectedStep, setSelectedStep] = useState<string>("grayscale");
  const [stepParams, setStepParams] = useState<Record<string, unknown>>({});
  const [stepResult, setStepResult] = useState<{
    image: string;
    metadata: Record<string, unknown>;
    time_ms: number;
  } | null>(null);
  const [stepLoading, setStepLoading] = useState(false);

  const [pipelineConfigs, setPipelineConfigs] = useState<Record<string, Record<string, unknown>>>(
    {},
  );
  const [pipelineEnabled, setPipelineEnabled] = useState<Record<string, boolean>>({});
  const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[] | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);

  useEffect(() => {
    getPreprocessSteps().then((s) => {
      setSteps(s);
      if (s.length > 0 && s[0]) setSelectedStep(s[0].name);
    });
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
      merged[step.name] = {
        ...pipelineConfigs[step.name],
        enabled: pipelineEnabled[step.name] ?? true,
      };
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

  if (steps.length === 0) return <FormSkeleton />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-ink">Preprocessing Playground</h1>
        <Button variant="ghost" onClick={handleExport}>
          Export YAML
        </Button>
      </div>

      <SingleImageUpload
        imageDataUrl={sourceImage}
        fileName={sourceFile?.name ?? ""}
        showPaste={true}
        onImageChange={(dataUrl, file) => {
          setSourceImage(dataUrl);
          setSourceFile(file);
          setStepResult(null);
          setPipelineResults(null);
        }}
      />

      {steps.length > 0 && (
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {steps.map((s, i) => (
            <Fragment key={s.name}>
              {i > 0 && <span className="text-sand mx-1">&rarr;</span>}
              <button
                onClick={() => {
                  setSelectedStep(s.name);
                  setStepParams({});
                  setStepResult(null);
                }}
                className={`
                  shrink-0 px-3 py-1.5 rounded-md text-sm font-medium transition-colors whitespace-nowrap
                  ${
                    selectedStep === s.name
                      ? "bg-indigo text-snow"
                      : "bg-snow text-charcoal border border-linen hover:bg-cream"
                  }
                `}
              >
                {s.label}
              </button>
            </Fragment>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4">
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
          <Button onClick={handlePreviewStep} disabled={!sourceFile || stepLoading}>
            {stepLoading ? "Processing..." : "Preview Step"}
          </Button>
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
              <div className="text-xs text-sand">
                {stepResult.time_ms}ms &middot;{" "}
                {Object.entries(stepResult.metadata)
                  .map(([k, v]) => `${k}: ${String(v)}`)
                  .join(" \u00b7 ")}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 space-y-4">
        <h2 className="font-display text-lg font-semibold text-ink">Full Pipeline</h2>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {steps.map((s) => (
            <PreprocessStepCard
              key={s.name}
              step={s}
              params={pipelineConfigs[s.name] || {}}
              enabled={pipelineEnabled[s.name] ?? true}
              onParamsChange={(p) => setPipelineConfigs((prev) => ({ ...prev, [s.name]: p }))}
              onEnabledChange={(e) => setPipelineEnabled((prev) => ({ ...prev, [s.name]: e }))}
            />
          ))}
        </div>
        <Button onClick={handlePreviewPipeline} disabled={!sourceFile || pipelineLoading}>
          {pipelineLoading ? "Processing..." : "Preview Pipeline"}
        </Button>
        {pipelineResults && (
          <div>
            <h3 className="mb-2 text-sm font-medium text-ink">Pipeline Result</h3>
            <PipelineFilmstrip steps={pipelineResults} />
          </div>
        )}
      </div>
    </div>
  );
}
