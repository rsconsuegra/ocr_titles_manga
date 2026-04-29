import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { cancelRun, getRunDetail, overrideResult, triggerPipeline } from "../api/pipeline";
import type { PostProcessingResultDetail, RunDetailResponse } from "../api/types";
import OcrResultCard from "../components/OcrResultCard";
import { DsoButton, DsoCard, DsoErrorBanner, DsoInput } from "../components/dso";
import RunStatusBadge from "../components/RunStatusBadge";

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
      getRunDetail(id).then(setRun).catch(() => {});
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
              ? { ...pp, title_en: updated.title_en, title_ja: updated.title_ja, code: updated.code }
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

  if (loading) return <p className="tech-label breathing">Loading...</p>;
  if (error) return <DsoErrorBanner>{error}</DsoErrorBanner>;
  if (!run) return <p className="text-sm text-muted">Run not found.</p>;

  return (
    <div>
      <button
        onClick={() => navigate("/runs")}
        className="mb-4 text-sm text-teal hover:text-bright transition-colors"
      >
        &larr; Back to Runs
      </button>

      <DsoCard className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-lg font-bold text-bright" title={run.id}>
            {run.id.slice(0, 8)}
          </h1>
          <RunStatusBadge status={run.status} />
          {(run.status === "pending" || run.status === "processing") && (
            <DsoButton variant="amber" onClick={handleCancel} disabled={cancelling}>
              {cancelling ? "Cancelling..." : "Cancel"}
            </DsoButton>
          )}
          {(["failed", "completed", "cancelled"] as const).includes(run.status as "failed" | "completed" | "cancelled") && (
            <DsoButton variant="amber" onClick={handleRetry} disabled={retrying}>
              {retrying ? "Retrying..." : "Retry"}
            </DsoButton>
          )}
        </div>
        <div className="mt-2 text-xs text-muted">
          Created: {new Date(run.created_at).toLocaleString()}
          {run.completed_at && ` | Completed: ${new Date(run.completed_at).toLocaleString()}`}
        </div>
        {run.error_message && (
          <DsoErrorBanner className="mt-2">{run.error_message}</DsoErrorBanner>
        )}
        <div className="mt-2 text-xs text-muted">Image: {run.input_image_path}</div>
      </DsoCard>

      {run.ocr_results.length === 0 && run.status === "processing" && (
        <p className="text-sm text-teal breathing">Processing...</p>
      )}

      {run.ocr_results.map((ocr) => (
        <div key={ocr.id} className="mb-4">
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
            <div key={pp.id} className="mt-3 neo-inset rounded-lg p-3">
              <div className="mb-1 flex items-center gap-2">
                <span className="tech-label-bright">{pp.processing_type}</span>
              </div>
              <div className="text-sm">
                <p><span className="text-muted">EN:</span> <span className="text-bright">{pp.title_en || "\u2014"}</span></p>
                <p><span className="text-muted">JA:</span> <span className="text-bright">{pp.title_ja || "\u2014"}</span></p>
                <p><span className="text-muted">Code:</span> <span className="text-bright">{pp.code || "\u2014"}</span></p>
              </div>

              {editingResult === pp.id ? (
                <div className="mt-2 space-y-2">
                  <DsoInput
                    placeholder="Title EN"
                    value={overrideForm.title_en}
                    onChange={(e) => setOverrideForm({ ...overrideForm, title_en: e.target.value })}
                  />
                  <DsoInput
                    placeholder="Title JA"
                    value={overrideForm.title_ja}
                    onChange={(e) => setOverrideForm({ ...overrideForm, title_ja: e.target.value })}
                  />
                  <DsoInput
                    placeholder="Code / ISBN"
                    value={overrideForm.code}
                    onChange={(e) => setOverrideForm({ ...overrideForm, code: e.target.value })}
                  />
                  <div className="flex gap-2">
                    <DsoButton
                      onClick={() => handleSave(pp.id)}
                      disabled={saving}
                    >
                      {saving ? "Saving..." : saved ? "Saved!" : "Save Override"}
                    </DsoButton>
                    <DsoButton variant="secondary" onClick={() => setEditingResult(null)}>
                      Cancel
                    </DsoButton>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => startEdit(pp)}
                  className="mt-2 text-xs text-teal hover:text-bright transition-colors"
                >
                  Edit / Override
                </button>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
