import ConfidenceMeter from "./ConfidenceMeter";
import { DsoCard, DsoErrorBanner } from "./dso";

interface OcrResultCardProps {
  modelName: string;
  processingTimeMs: number;
  confidence: number;
  rawText: string;
  error?: string | null;
  variant?: "full" | "compact";
}

export default function OcrResultCard({
  modelName,
  processingTimeMs,
  confidence,
  rawText,
  error,
  variant = "compact",
}: OcrResultCardProps) {
  if (variant === "full") {
    return (
      <DsoCard>
        <h3 className="mb-2 text-sm font-semibold text-bright">OCR Output</h3>
        <div className="mb-2">
          <span className="text-xs text-muted">Model:</span>{" "}
          <span className="text-sm font-medium text-bright">{modelName}</span>
        </div>
        <div className="mb-2">
          <span className="text-xs text-muted">Time:</span>{" "}
          <span className="text-sm text-bright">{processingTimeMs}ms</span>
        </div>
        <div className="mb-3">
          <span className="text-xs text-muted">Confidence:</span>
          <ConfidenceMeter value={confidence} />
        </div>
        <div className="rounded bg-lcd p-3">
          <pre className="whitespace-pre-wrap break-words text-sm text-bright/80">
            {rawText || "(empty)"}
          </pre>
        </div>
        {error && <DsoErrorBanner className="mt-2">{error}</DsoErrorBanner>}
      </DsoCard>
    );
  }

  return (
    <DsoCard>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-bright">{modelName}</h3>
        <ConfidenceMeter value={confidence} />
      </div>
      <div className="text-xs text-muted mb-2">{processingTimeMs}ms</div>
      <div className="rounded bg-lcd p-3">
        <pre className="whitespace-pre-wrap break-words text-sm text-bright/80">
          {rawText || "(empty)"}
        </pre>
      </div>
      {error && <DsoErrorBanner className="mt-2">{error}</DsoErrorBanner>}
    </DsoCard>
  );
}
