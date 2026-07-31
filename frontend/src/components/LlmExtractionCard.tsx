import { useState } from "react";

import ConfidenceMeter from "./ConfidenceMeter";
import ErrorBanner from "./ui/ErrorBanner";
import { Card } from "./ui";

interface LlmExtractionCardProps {
  titleEn?: string | null;
  titleJa?: string | null;
  code?: string | null;
  confidence: number;
  method?: string;
  rawResponse?: string | null;
  extraMetadata?: Record<string, string> | null;
  error?: string | null;
}

const LABEL_OVERRIDES: Record<string, string> = {
  author: "Author",
  social_page: "Social Page",
};

function formatLabel(key: string): string {
  if (LABEL_OVERRIDES[key]) return LABEL_OVERRIDES[key];
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function LlmExtractionCard({
  titleEn,
  titleJa,
  code,
  confidence,
  method,
  rawResponse,
  extraMetadata,
  error,
}: LlmExtractionCardProps) {
  const [showRaw, setShowRaw] = useState(false);
  const hasStructuredData = !!(titleEn || titleJa || code);
  const hasRawResponse = !!rawResponse && rawResponse.trim().length > 0;

  return (
    <Card accent="indigo">
      <h3 className="mb-2 text-sm font-semibold text-indigo">LLM Extraction</h3>
      {error && (
        <div className="mb-3">
          <ErrorBanner message={error} />
        </div>
      )}
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
        {extraMetadata &&
          Object.entries(extraMetadata).map(([key, value]) => (
            <div key={key}>
              <span className="text-sand">{formatLabel(key)}:</span>{" "}
              <span className="font-medium text-charcoal">{value}</span>
            </div>
          ))}
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
