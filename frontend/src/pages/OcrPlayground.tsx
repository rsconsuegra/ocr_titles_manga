import { useEffect, useRef, useState } from "react";

import { exportOCRConfig, getOCRModels, runOCR } from "../api/ocr";
import type { ModelDescriptorResponse, OCRRunResponse } from "../api/types";
import { DsoButton, DsoCard, DsoErrorBanner, DsoSelect } from "../components/dso";
import ConfidenceMeter from "../components/ConfidenceMeter";
import PreprocessStepCard from "../components/PreprocessStepCard";
import { useFileReader } from "../hooks/useFileReader";

export default function OcrPlayground() {
  const [models, setModels] = useState<ModelDescriptorResponse[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("");
  const [imageDataUrl, setImageDataUrl] = useState<string>("");
  const [params, setParams] = useState<Record<string, Record<string, unknown>>>({});
  const [enableLlm, setEnableLlm] = useState(false);
  const [result, setResult] = useState<OCRRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const readFile = useFileReader();

  useEffect(() => {
    getOCRModels()
      .then((data) => {
        setModels(data);
        const sel = data.find((m) => m.available && m.enabled);
        setSelectedModel(sel?.name || (data[0]?.name ?? ""));
      })
      .catch(() => setError("Failed to load OCR models"));
  }, []);

  const currentModel = models.find((m) => m.name === selectedModel);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const dataUrl = await readFile(file);
    setImageDataUrl(dataUrl);
    setResult(null);
  }

  async function handleRun() {
    if (!imageDataUrl || !selectedModel) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await runOCR(imageDataUrl, selectedModel, params[selectedModel] || {}, enableLlm);
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

  const cbx = "rounded border-highlight/40 bg-inset accent-teal";

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-bright">OCR Playground</h1>
        <DsoButton variant="secondary" onClick={handleExport}>
          Export Config
        </DsoButton>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div>
            <p className="tech-label mb-1">Image</p>
            <input ref={fileRef} type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
            <DsoButton variant="secondary" onClick={() => fileRef.current?.click()}>
              {imageDataUrl ? "Change Image" : "Upload Image"}
            </DsoButton>
            {imageDataUrl && (
              <img src={imageDataUrl} alt="Preview" className="mt-2 max-h-48 rounded border border-highlight/20" />
            )}
          </div>

          <DsoSelect
            label="Model"
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {models.map((m) => (
              <option key={m.name} value={m.name} disabled={!m.available}>
                {m.label} {!m.available ? "(not available)" : !m.enabled ? "(disabled)" : ""}
              </option>
            ))}
          </DsoSelect>

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

          <label className="flex items-center gap-2 text-sm text-bright">
            <input type="checkbox" checked={enableLlm} onChange={(e) => setEnableLlm(e.target.checked)} className={cbx} />
            Post-process with LLM
          </label>

          <DsoButton onClick={handleRun} disabled={loading || !imageDataUrl || !selectedModel} className="w-full">
            {loading ? "Running OCR..." : "Run OCR"}
          </DsoButton>
        </div>

        <div className="space-y-4">
          {error && <DsoErrorBanner>{error}</DsoErrorBanner>}

          {result && (
            <>
              <DsoCard>
                <h3 className="mb-2 text-sm font-semibold text-bright">OCR Output</h3>
                <div className="mb-2">
                  <span className="text-xs text-muted">Model:</span>{" "}
                  <span className="text-sm font-medium text-bright">{result.ocr.model_name}</span>
                </div>
                <div className="mb-2">
                  <span className="text-xs text-muted">Time:</span>{" "}
                  <span className="text-sm text-bright">{result.ocr.processing_time_ms}ms</span>
                </div>
                <div className="mb-3">
                  <span className="text-xs text-muted">Confidence:</span>
                  <ConfidenceMeter value={result.ocr.confidence} />
                </div>
                <div className="rounded bg-lcd p-3">
                  <pre className="whitespace-pre-wrap break-words text-sm text-bright/80">
                    {result.ocr.raw_text || "(empty)"}
                  </pre>
                </div>
                {result.ocr.error && (
                  <DsoErrorBanner className="mt-2">{result.ocr.error}</DsoErrorBanner>
                )}
              </DsoCard>

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
                    <div>
                      <span className="text-muted">Method:</span> <span className="text-bright">{result.llm.source_method}</span>
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
