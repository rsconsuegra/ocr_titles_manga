import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createBatch } from "../api/batch";
import { triggerPipeline, uploadImages } from "../api/pipeline";
import { listProfiles } from "../api/profiles";
import type { PipelineRunResponse, ProfileResponse } from "../api/types";
import { DsoBadge, DsoButton, DsoCard, DsoErrorBanner, DsoInput, DsoSelect, DsoTable } from "../components/dso";
import ImageUploader from "../components/ImageUploader";
import RunStatusBadge from "../components/RunStatusBadge";

export default function Upload() {
  const navigate = useNavigate();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
  const [triggeredRuns, setTriggeredRuns] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [batchName, setBatchName] = useState("");
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  useEffect(() => {
    listProfiles().then((res) => setProfiles(res.items)).catch(() => {});
  }, []);

  async function handleUpload() {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadImages(
        selectedFiles,
        selectedProfileId || undefined,
      );
      setRuns(result);
      setSelectedFiles([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleBatchUpload() {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const batch = await createBatch(
        selectedFiles,
        batchName.trim() || undefined,
        selectedProfileId || undefined,
      );
      navigate(`/batches/${batch.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function handleTrigger(runId: string) {
    try {
      await triggerPipeline(runId);
      setTriggeredRuns((prev) => new Set(prev).add(runId));
      setRuns((prev) => prev.map((r) => (r.id === runId ? { ...r, status: "processing" } : r)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trigger failed");
    }
  }

  return (
    <div>
      <h1 className="mb-4 font-display text-xl font-bold text-bright">Upload Manga Images</h1>

      <ImageUploader onFilesSelected={setSelectedFiles} />

      {profiles.length > 0 && (
        <div className="mt-3">
          <DsoSelect
            label="Profile"
            value={selectedProfileId}
            onChange={(e) => setSelectedProfileId(e.target.value)}
          >
            <option value="">Use global config</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}{p.is_default ? " (default)" : ""}
              </option>
            ))}
          </DsoSelect>
        </div>
      )}

      {selectedProfile && (
        <DsoCard variant="lcd" className="mt-3">
          <h3 className="mb-2 text-sm font-semibold text-teal">
            {selectedProfile.name}
          </h3>
          {selectedProfile.description && (
            <p className="mb-2 text-xs text-muted">{selectedProfile.description}</p>
          )}
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div>
              <p className="mb-1 tech-label">Preprocessing</p>
              {selectedProfile.preprocess_steps && Object.keys(selectedProfile.preprocess_steps).length > 0 ? (
                <ul className="space-y-0.5">
                  {Object.entries(selectedProfile.preprocess_steps).map(([step, cfg]) => (
                    <li key={step} className={((cfg as Record<string, unknown>).enabled === false) ? "text-muted line-through" : "text-bright"}>
                      {step}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None</p>
              )}
            </div>
            <div>
              <p className="mb-1 tech-label">OCR Models</p>
              {selectedProfile.ocr_models && Object.keys(selectedProfile.ocr_models).length > 0 ? (
                <ul className="space-y-0.5">
                  {Object.entries(selectedProfile.ocr_models).map(([model, cfg]) => (
                    <li key={model} className={((cfg as Record<string, unknown>).enabled === false) ? "text-muted line-through" : "text-bright"}>
                      {model}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted">None</p>
              )}
            </div>
            <div>
              <p className="mb-1 tech-label">LLM</p>
              <DsoBadge variant={selectedProfile.enable_llm ? "completed" : "default"}>
                {selectedProfile.enable_llm ? "Enabled" : "Disabled"}
              </DsoBadge>
            </div>
          </div>
        </DsoCard>
      )}

      {selectedFiles.length > 0 && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-2">
            <DsoInput
              placeholder="Batch name (optional)"
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              className="max-w-xs"
            />
            <DsoButton onClick={handleBatchUpload} disabled={uploading}>
              {uploading ? "Uploading..." : "Create Batch"}
            </DsoButton>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted">or</span>
            <DsoButton onClick={handleUpload} disabled={uploading}>
              {uploading ? "Uploading..." : "Upload Individually"}
            </DsoButton>
          </div>
        </div>
      )}

      {error && <DsoErrorBanner className="mt-4">{error}</DsoErrorBanner>}

      {runs.length > 0 && (
        <div className="mt-6">
          <h2 className="mb-3 font-display text-lg font-semibold text-bright">Uploaded Runs</h2>
          <DsoTable
            columns={[
              {
                header: "#",
                render: (_, i) => <span className="tabular-nums text-muted">{i + 1}</span>,
              },
              {
                header: "Image",
                render: (run: PipelineRunResponse) => (
                  <span className="max-w-32 truncate">{run.input_image_path.split("/").pop()}</span>
                ),
              },
              {
                header: "Run ID",
                render: (run: PipelineRunResponse) => (
                  <span className="font-mono text-xs">{run.id.slice(0, 8)}</span>
                ),
              },
              {
                header: "Status",
                render: (run: PipelineRunResponse) => <RunStatusBadge status={run.status} />,
              },
              {
                header: "Action",
                render: (run: PipelineRunResponse) =>
                  triggeredRuns.has(run.id) ? (
                    <span className="text-xs text-teal breathing">Processing...</span>
                  ) : (
                    <DsoButton
                      className="px-3 py-1 text-xs"
                      onClick={() => handleTrigger(run.id)}
                    >
                      Trigger Pipeline
                    </DsoButton>
                  ),
              },
            ]}
            data={runs}
            keyFn={(run) => run.id}
          />
        </div>
      )}
    </div>
  );
}
