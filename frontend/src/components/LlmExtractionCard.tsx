import { useState } from "react";

import ConfidenceMeter from "./ConfidenceMeter";
import { Card } from "./ui";

interface LlmExtractionCardProps {
  titleEn?: string | null;
  titleJa?: string | null;
  code?: string | null;
  confidence: number;
  method?: string;
  rawResponse?: string | null;
}

export default function LlmExtractionCard({
  titleEn,
  titleJa,
  code,
  confidence,
  method,
  rawResponse,
}: LlmExtractionCardProps) {
  const [showRaw, setShowRaw] = useState(false);
  const hasStructuredData = !!(titleEn || titleJa || code);
  const hasRawResponse = !!rawResponse && rawResponse.trim().length > 0;

  return (
    <Card accent="indigo">
      <h3 className="mb-2 text-sm font-semibold text-indigo">LLM Extraction</h3>
      <div className="space-y-1 text-sm">
        {titleEn && (
          <div>
            <span className="text-sand">Title (EN):</span>{" "}
            <span className="font-medium text-charcoal">{titleEn}</span>
          </div>
        )}
        {titleJa && (
          <div>
            <span className="text-sand">Title (JA):</span>{" "}
            <span className="font-medium text-charcoal">{titleJa}</span>
          </div>
        )}
        {code && (
          <div>
            <span className="text-sand">Code:</span>{" "}
            <span className="font-mono text-charcoal">{code}</span>
          </div>
        )}
        <div>
          <span className="text-sand">Confidence:</span>
          <ConfidenceMeter value={confidence} />
        </div>
        {method && (
          <div>
            <span className="text-sand">Method:</span>{" "}
            <span className="text-charcoal">{method}</span>
          </div>
        )}
        {hasRawResponse && !hasStructuredData && (
          <div className="mt-2">
            <button
              type="button"
              className="text-xs text-indigo hover:underline cursor-pointer"
              onClick={() => setShowRaw(!showRaw)}
            >
              {showRaw ? "Hide" : "Show"} raw LLM output
            </button>
            {showRaw && (
              <pre className="mt-1 whitespace-pre-wrap rounded bg-linen p-2 text-xs text-charcoal">
                {rawResponse}
              </pre>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
