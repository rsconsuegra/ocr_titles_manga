import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { cancelRun, getRunDetail, overrideResult, triggerPipeline } from "../api/pipeline";
import type { PostProcessingResultDetail, RunDetailResponse } from "../api/types";
import LlmExtractionCard from "../components/LlmExtractionCard";
import OcrResultCard from "../components/OcrResultCard";
import RunStatusBadge from "../components/RunStatusBadge";
import { Button, Card, ErrorBanner, Input, RunDetailSkeleton } from "../components/ui";

export default function RunDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [run, setRun] = useState<RunDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingResult, setEditingResult] = useState<string | null>(null);
  const [overrideForm, setOverrideForm] = useState({ title_en: "", title_ja: "", code: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedOcr, setExpandedOcr] = useState<Record<string, boolean>>({});
  const editTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  /* eslint-disable react-hooks/set-state-in-effect -- data-fetching effect */
  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getRunDetail(id)
      .then(setRun)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);
  /* eslint-enable react-hooks/set-state-in-effect */

  const isActive = run?.status === "pending" || run?.status === "processing";

  /* eslint-disable react-hooks/exhaustive-deps -- run is only a guard, isActive tracks state */
  useEffect(() => {
    if (!run || !id || !isActive) return;
    const interval = setInterval(() => {
      getRunDetail(id)
        .then(setRun)
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [isActive, id]);
  /* eslint-enable react-hooks/exhaustive-deps */

  useEffect(() => {
    return () => {
      if (editTimeoutRef.current) clearTimeout(editTimeoutRef.current);
    };
  }, []);

  function startEdit(pp: PostProcessingResultDetail) {
    setEditingResult(pp.id);
    setOverrideForm({
      title_en: pp.title_en || "",
      title_ja: pp.title_ja || "",
      code: pp.code || "",
    });
    setSaved(false);
  }

  async function handleSave(resultId: string) {
    setSaving(true);
    try {
      const updated = await overrideResult(resultId, overrideForm);
      if (run) {
        const newRun = { ...run };
        newRun.ocr_results = newRun.ocr_results.map((ocr) => ({
          ...ocr,
          post_processing_results: ocr.post_processing_results.map((pp) =>
            pp.id === updated.id
              ? {
                  ...pp,
                  title_en: updated.title_en,
                  title_ja: updated.title_ja,
                  code: updated.code,
                }
              : pp,
          ),
        }));
        setRun(newRun);
      }
      setSaved(true);
      editTimeoutRef.current = setTimeout(() => setEditingResult(null), 1000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleRetry() {
    if (!id) return;
    setRetrying(true);
    setError(null);
    try {
      await triggerPipeline(id);
      const updated = await getRunDetail(id);
      setRun(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetrying(false);
    }
  }

  async function handleCancel() {
    if (!id) return;
    setCancelling(true);
    setError(null);
    try {
      await cancelRun(id);
      const updated = await getRunDetail(id);
      setRun(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    } finally {
      setCancelling(false);
    }
  }

  if (loading) return <RunDetailSkeleton />;
  if (error) return <ErrorBanner message={error} />;
  if (!run) return <p className="text-sm text-sand">Run not found.</p>;

  return (
    <div className="space-y-6">
      <button
        onClick={() => navigate("/runs")}
        className="text-sm text-indigo hover:text-ink transition-colors font-body"
      >
        &larr; Back to Runs
      </button>

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-2">
          <Card>
            <img
              src={`/api/v1/pipeline/runs/${run.id}/image`}
              alt="Input"
              className="w-full rounded-md"
            />
          </Card>
        </div>

        <div className="col-span-3 space-y-4">
          <Card>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <h1 className="font-mono text-lg font-bold text-ink" title={run.id}>
                  {run.id.slice(0, 8)}
                </h1>
                <RunStatusBadge status={run.status} />
              </div>
              <div>
                <span className="label-text">Created</span>
                <p className="text-sm text-charcoal font-body">
                  {new Date(run.created_at).toLocaleString()}
                </p>
              </div>
              {run.completed_at && (
                <div>
                  <span className="label-text">Completed</span>
                  <p className="text-sm text-charcoal font-body">
                    {new Date(run.completed_at).toLocaleString()}
                  </p>
                </div>
              )}
              <div className="flex gap-2 pt-2">
                {(run.status === "pending" || run.status === "processing") && (
                  <Button variant="secondary" onClick={handleCancel} disabled={cancelling}>
                    {cancelling ? "Cancelling..." : "Cancel"}
                  </Button>
                )}
                {(["failed", "completed", "cancelled"] as const).includes(
                  run.status as "failed" | "completed" | "cancelled",
                ) && (
                  <Button variant="secondary" onClick={handleRetry} disabled={retrying}>
                    {retrying ? "Retrying..." : "Retry"}
                  </Button>
                )}
              </div>
            </div>
            {run.error_message && (
              <div className="mt-3">
                <ErrorBanner message={run.error_message} />
              </div>
            )}
          </Card>

          {run.ocr_results.length === 0 && run.status === "processing" && (
            <p className="text-sm text-indigo fade-pulse">Processing...</p>
          )}

          {run.ocr_results.map((ocr) => (
            <Card key={ocr.id} padding="sm">
              <button
                onClick={() => setExpandedOcr((prev) => ({ ...prev, [ocr.id]: !prev[ocr.id] }))}
                className="w-full flex items-center justify-between py-1 text-left"
              >
                <span className="font-display font-semibold text-ink">{ocr.model_name}</span>
                <span className="text-sand text-sm">
                  {expandedOcr[ocr.id] !== false ? "\u2212" : "+"}
                </span>
              </button>
              {expandedOcr[ocr.id] !== false && (
                <div className="pt-3 mt-2 border-t border-linen">
                  <OcrResultCard
                    modelName={ocr.model_name}
                    processingTimeMs={ocr.processing_time_ms}
                    confidence={ocr.confidence}
                    rawText={ocr.raw_text}
                    error={ocr.error}
                    blocks={ocr.blocks}
                    imageDataUrl={`/api/v1/pipeline/runs/${run.id}/image`}
                    variant={ocr.blocks && ocr.blocks.length > 0 ? "full" : "compact"}
                  />
                  {ocr.post_processing_results.map((pp) => (
                    <div key={pp.id} className="mt-3">
                      <LlmExtractionCard
                        titleEn={pp.title_en}
                        titleJa={pp.title_ja}
                        code={pp.code}
                        confidence={pp.confidence}
                        method={pp.processing_type}
                        rawResponse={pp.raw_response}
                      />
                      {editingResult === pp.id ? (
                        <div className="mt-3 pt-3 border-t border-linen space-y-3">
                          <Input
                            label="Title (EN)"
                            value={overrideForm.title_en}
                            onChange={(e) =>
                              setOverrideForm({ ...overrideForm, title_en: e.target.value })
                            }
                          />
                          <Input
                            label="Title (JA)"
                            value={overrideForm.title_ja}
                            onChange={(e) =>
                              setOverrideForm({ ...overrideForm, title_ja: e.target.value })
                            }
                          />
                          <Input
                            label="Code / ISBN"
                            value={overrideForm.code}
                            onChange={(e) =>
                              setOverrideForm({ ...overrideForm, code: e.target.value })
                            }
                          />
                          <div className="flex gap-2">
                            <Button onClick={() => handleSave(pp.id)} disabled={saving}>
                              {saving ? "Saving..." : saved ? "Saved!" : "Save Override"}
                            </Button>
                            <Button variant="ghost" onClick={() => setEditingResult(null)}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => startEdit(pp)}
                          className="mt-2 text-xs text-indigo hover:text-ink transition-colors font-body"
                        >
                          Edit / Override
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
