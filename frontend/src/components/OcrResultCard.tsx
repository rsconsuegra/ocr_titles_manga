import { useRef, useState } from "react";

import type { TextBlockData } from "../api/types";
import ConfidenceMeter from "./ConfidenceMeter";
import { DsoButton, DsoCard, DsoErrorBanner } from "./dso";

interface OcrResultCardProps {
  modelName: string;
  processingTimeMs: number;
  confidence: number;
  rawText: string;
  error?: string | null;
  blocks?: TextBlockData[] | null;
  imageDataUrl?: string;
  variant?: "full" | "compact";
}

function BboxOverlay({
  blocks,
  imageDataUrl,
}: {
  blocks: TextBlockData[];
  imageDataUrl: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [loaded, setLoaded] = useState(false);

  function handleImageLoad() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = canvas.querySelector("img") as HTMLImageElement;
    if (!img) return;

    const displayWidth = canvas.clientWidth;
    const scale = displayWidth / img.naturalWidth;
    const displayHeight = img.naturalHeight * scale;

    canvas.width = img.naturalWidth;
    canvas.height = img.naturalHeight;
    canvas.style.height = `${displayHeight}px`;

    ctx.drawImage(img, 0, 0);

    blocks.forEach((block) => {
      const pts = block.bbox;
      ctx.beginPath();
      ctx.moveTo(pts[0]![0]!, pts[0]![1]!);
      for (let i = 1; i < pts.length; i++) {
        ctx.lineTo(pts[i]![0]!, pts[i]![1]!);
      }
      ctx.closePath();
      ctx.strokeStyle = "#06b6d4";
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    setLoaded(true);
  }

  return (
    <div className="relative">
      <canvas ref={canvasRef} className="w-full rounded border border-border">
        <img src={imageDataUrl} alt="" className="hidden" onLoad={handleImageLoad} />
      </canvas>
      {!loaded && (
        <div className="flex h-40 items-center justify-center text-sm text-muted">
          Loading overlay...
        </div>
      )}
    </div>
  );
}

export default function OcrResultCard({
  modelName,
  processingTimeMs,
  confidence,
  rawText,
  error,
  blocks,
  imageDataUrl,
  variant = "compact",
}: OcrResultCardProps) {
  const [showOverlay, setShowOverlay] = useState(false);
  const [hoveredBlock, setHoveredBlock] = useState<number | null>(null);
  const hasBlocks = blocks && blocks.length > 0;

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

        {hasBlocks && (
          <div className="mb-3">
            <div className="mb-2 flex items-center gap-2">
              <DsoButton
                variant="secondary"
                onClick={() => setShowOverlay(!showOverlay)}
              >
                {showOverlay ? "Hide Overlay" : "Show Bounding Boxes"}
              </DsoButton>
              <span className="text-xs text-muted">
                {blocks!.length} text block{blocks!.length !== 1 ? "s" : ""} detected
              </span>
            </div>

            {showOverlay && imageDataUrl && (
              <BboxOverlay blocks={blocks!} imageDataUrl={imageDataUrl} />
            )}

            <div className="mt-2 max-h-60 overflow-auto rounded border border-border">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-left text-muted">
                    <th className="px-2 py-1">#</th>
                    <th className="px-2 py-1">Text</th>
                    <th className="px-2 py-1">Conf</th>
                    <th className="px-2 py-1">Position</th>
                  </tr>
                </thead>
                <tbody>
                  {blocks!.map((b, i) => (
                    <tr
                      key={i}
                      className={`border-t border-border ${
                        hoveredBlock === i ? "bg-cyan-500/10" : ""
                      }`}
                      onMouseEnter={() => setHoveredBlock(i)}
                      onMouseLeave={() => setHoveredBlock(null)}
                    >
                      <td className="px-2 py-1 text-muted">{i + 1}</td>
                      <td className="max-w-[200px] truncate px-2 py-1 text-bright">
                        {b.text}
                      </td>
                      <td className="px-2 py-1 text-bright">
                        {(b.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="px-2 py-1 font-mono text-muted">
                        [{b.bbox[0]!.map((v) => Math.round(v)).join(", ")}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

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
