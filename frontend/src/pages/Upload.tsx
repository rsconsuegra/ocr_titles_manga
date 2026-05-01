import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createBatch } from "../api/batch";
import { triggerPipeline, uploadImages } from "../api/pipeline";
import { listProfiles } from "../api/profiles";
import type { PipelineRunResponse, ProfileResponse } from "../api/types";
import RunStatusBadge from "../components/RunStatusBadge";
import { Badge, Button, Card, ErrorBanner, Input, Select, Table } from "../components/ui";

export default function Upload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [blobUrls, setBlobUrls] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [runs, setRuns] = useState<PipelineRunResponse[]>([]);
  const [triggeredRuns, setTriggeredRuns] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [batchName, setBatchName] = useState("");
  const [profiles, setProfiles] = useState<ProfileResponse[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const selectedProfile = profiles.find((p) => p.id === selectedProfileId);

  useEffect(() => {
    listProfiles()
      .then((res) => setProfiles(res.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const urls = selectedFiles.map((f) => URL.createObjectURL(f));
    setBlobUrls(urls);
    return () => urls.forEach((u) => URL.revokeObjectURL(u));
  }, [selectedFiles]);

  function addFiles(files: FileList | File[]) {
    const arr = Array.from(files).filter((f) => /\.(png|jpe?g|webp|tiff?|bmp)$/i.test(f.name));
    setSelectedFiles((prev) => [...prev, ...arr]);
  }

  function removeFile(idx: number) {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleUpload() {
    if (selectedFiles.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const result = await uploadImages(selectedFiles, selectedProfileId || undefined);
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
    <div className="space-y-6">
      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-3 space-y-4">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              addFiles(e.dataTransfer.files);
            }}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            className={`
              border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors
              ${isDragging ? "border-indigo bg-indigo-pale/20" : "border-linen bg-cream hover:border-indigo/50"}
            `}
          >
            <svg
              className="mx-auto mb-3 h-10 w-10 text-sand"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p className="text-charcoal font-body">Drop images here</p>
            <p className="text-sand font-body text-sm mt-1">or click to browse</p>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".png,.jpg,.jpeg,.webp,.tiff,.tif,.bmp"
              onChange={(e) => {
                if (e.target.files) addFiles(e.target.files);
                e.target.value = "";
              }}
              className="hidden"
            />
          </div>

          {selectedFiles.length > 0 && (
            <div className="grid grid-cols-3 gap-3">
              {selectedFiles.map((f, i) => (
                <div key={i} className="group relative rounded-lg border border-linen bg-snow p-2">
                  <img
                    src={blobUrls[i]}
                    alt={f.name}
                    className="mb-1 h-24 w-full rounded object-cover"
                  />
                  <p className="truncate text-xs text-charcoal">{f.name}</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(i);
                    }}
                    className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-vermillion text-xs text-snow opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="col-span-2 space-y-4">
          <Card>
            <h3 className="font-display text-base font-semibold text-ink mb-4">Configuration</h3>

            {profiles.length > 0 && (
              <Select
                label="Profile"
                value={selectedProfileId}
                onChange={(e) => setSelectedProfileId(e.target.value)}
                options={[
                  { value: "", label: "Use global config" },
                  ...profiles.map((p) => ({
                    value: p.id,
                    label: `${p.name}${p.is_default ? " (default)" : ""}`,
                  })),
                ]}
              />
            )}

            {selectedProfile && (
              <div className="mt-4 pt-4 border-t border-linen">
                <h4 className="text-sm font-semibold text-ink mb-2">{selectedProfile.name}</h4>
                {selectedProfile.description && (
                  <p className="text-xs text-sand mb-3">{selectedProfile.description}</p>
                )}
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div>
                    <span className="label-text">Preprocessing</span>
                    {selectedProfile.preprocess_steps &&
                    Object.keys(selectedProfile.preprocess_steps).length > 0 ? (
                      <ul className="mt-1 space-y-0.5">
                        {Object.entries(selectedProfile.preprocess_steps).map(([step, cfg]) => (
                          <li
                            key={step}
                            className={
                              (cfg as Record<string, unknown>).enabled === false
                                ? "text-sand line-through"
                                : "text-charcoal"
                            }
                          >
                            {step}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sand mt-1">None</p>
                    )}
                  </div>
                  <div>
                    <span className="label-text">OCR Models</span>
                    {selectedProfile.ocr_models &&
                    Object.keys(selectedProfile.ocr_models).length > 0 ? (
                      <ul className="mt-1 space-y-0.5">
                        {Object.entries(selectedProfile.ocr_models).map(([model, cfg]) => (
                          <li
                            key={model}
                            className={
                              (cfg as Record<string, unknown>).enabled === false
                                ? "text-sand line-through"
                                : "text-charcoal"
                            }
                          >
                            {model}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sand mt-1">None</p>
                    )}
                  </div>
                  <div>
                    <span className="label-text">LLM</span>
                    <div className="mt-1">
                      <Badge status={selectedProfile.enable_llm ? "completed" : "default"}>
                        {selectedProfile.enable_llm ? "Enabled" : "Disabled"}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {selectedFiles.length > 0 && (
              <div className="mt-4 pt-4 border-t border-linen space-y-3">
                <Input
                  label="Batch name (optional)"
                  value={batchName}
                  onChange={(e) => setBatchName(e.target.value)}
                />
                <Button onClick={handleBatchUpload} disabled={uploading} className="w-full">
                  {uploading ? "Uploading..." : "Start Processing"}
                </Button>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-sand">or</span>
                  <Button variant="ghost" onClick={handleUpload} disabled={uploading}>
                    {uploading ? "Uploading..." : "Upload Individually"}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {runs.length > 0 && (
        <Card>
          <Card.Header title="Uploaded Runs" />
          <Table
            columns={[
              {
                key: "id",
                header: "#",
                render: (run) => (
                  <span className="tabular-nums text-sand">
                    {runs.indexOf(run as PipelineRunResponse) + 1}
                  </span>
                ),
              },
              {
                key: "input_image_path",
                header: "Image",
                render: (run: PipelineRunResponse) => (
                  <span className="max-w-32 truncate">{run.input_image_path.split("/").pop()}</span>
                ),
              },
              {
                key: "id",
                header: "Run ID",
                render: (run: PipelineRunResponse) => (
                  <span className="font-mono text-xs">{run.id.slice(0, 8)}</span>
                ),
              },
              {
                key: "status",
                header: "Status",
                render: (run: PipelineRunResponse) => <RunStatusBadge status={run.status} />,
              },
              {
                key: "id",
                header: "Action",
                render: (run: PipelineRunResponse) =>
                  triggeredRuns.has(run.id) ? (
                    <span className="text-xs text-indigo fade-pulse">Processing...</span>
                  ) : (
                    <Button className="px-3 py-1 text-xs" onClick={() => handleTrigger(run.id)}>
                      Trigger Pipeline
                    </Button>
                  ),
              },
            ]}
            data={runs}
          />
        </Card>
      )}
    </div>
  );
}
