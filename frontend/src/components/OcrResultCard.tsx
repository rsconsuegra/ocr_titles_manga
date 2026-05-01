import { useRef, useState } from "react";

import type { TextBlockData } from "../api/types";
import ConfidenceMeter from "./ConfidenceMeter";
import { Button, Card, ErrorBanner } from "./ui";

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

function BboxOverlay({ blocks, imageDataUrl }: { blocks: TextBlockData[]; imageDataUrl: string }) {
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
      ctx.strokeStyle = "rgba(255,255,255,0.6)";
      ctx.lineWidth = 4;
      ctx.stroke();
      ctx.strokeStyle = "#2E4A7A";
      ctx.lineWidth = 2;
      ctx.stroke();
    });

    setLoaded(true);
  }

  return (
    <div className="relative">
      <canvas ref={canvasRef} className="w-full rounded border border-linen">
        <img src={imageDataUrl} alt="" className="hidden" onLoad={handleImageLoad} />
      </canvas>
      {!loaded && (
        <div className="flex h-40 items-center justify-center text-sm text-sand">
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
      <Card>
        <h3 className="mb-2 text-sm font-semibold text-ink">OCR Output</h3>
        <div className="mb-2">
          <span className="text-xs text-sand">Model:</span>{" "}
          <span className="text-sm font-medium text-charcoal">{modelName}</span>
        </div>
        <div className="mb-2">
          <span className="text-xs text-sand">Time:</span>{" "}
          <span className="text-sm text-charcoal">{processingTimeMs}ms</span>
        </div>
        <div className="mb-3">
          <span className="text-xs text-sand">Confidence:</span>
          <ConfidenceMeter value={confidence} />
        </div>

        {hasBlocks && (
          <div className="mb-3">
            <div className="mb-2 flex items-center gap-2">
              <Button variant="secondary" onClick={() => setShowOverlay(!showOverlay)}>
                {showOverlay ? "Hide Overlay" : "Show Bounding Boxes"}
              </Button>
              <span className="text-xs text-sand">
                {blocks!.length} text block{blocks!.length !== 1 ? "s" : ""} detected
              </span>
            </div>

            {showOverlay && imageDataUrl && (
              <BboxOverlay blocks={blocks!} imageDataUrl={imageDataUrl} />
            )}

            <div className="mt-2 max-h-60 overflow-auto rounded border border-linen">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-snow">
                  <tr className="text-left text-sand">
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
                      className={`border-t border-linen ${
                        hoveredBlock === i ? "bg-indigo-pale/50" : ""
                      }`}
                      onMouseEnter={() => setHoveredBlock(i)}
                      onMouseLeave={() => setHoveredBlock(null)}
                    >
                      <td className="px-2 py-1 text-sand">{i + 1}</td>
                      <td className="max-w-[200px] truncate px-2 py-1 text-charcoal">{b.text}</td>
                      <td className="px-2 py-1 text-charcoal">
                        {(b.confidence * 100).toFixed(1)}%
                      </td>
                      <td className="px-2 py-1 font-mono text-sand">
                        [{b.bbox[0]!.map((v) => Math.round(v)).join(", ")}]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        <div className="rounded bg-cream p-3">
          <pre className="whitespace-pre-wrap break-words text-sm text-charcoal/80">
            {rawText || "(empty)"}
          </pre>
        </div>
        {error && (
          <div className="mt-2">
            <ErrorBanner message={error} />
          </div>
        )}
      </Card>
    );
  }

  return (
    <Card>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink">{modelName}</h3>
        <ConfidenceMeter value={confidence} />
      </div>
      <div className="text-xs text-sand mb-2">{processingTimeMs}ms</div>
      <div className="rounded bg-cream p-3">
        <pre className="whitespace-pre-wrap break-words text-sm text-charcoal/80">
          {rawText || "(empty)"}
        </pre>
      </div>
      {error && (
        <div className="mt-2">
          <ErrorBanner message={error} />
        </div>
      )}
    </Card>
  );
}
