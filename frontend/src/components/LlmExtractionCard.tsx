import ConfidenceMeter from "./ConfidenceMeter";
import { DsoCard } from "./dso";

interface LlmExtractionCardProps {
  titleEn?: string | null;
  titleJa?: string | null;
  code?: string | null;
  confidence: number;
  method?: string;
}

export default function LlmExtractionCard({
  titleEn,
  titleJa,
  code,
  confidence,
  method,
}: LlmExtractionCardProps) {
  return (
    <DsoCard variant="lcd">
      <h3 className="mb-2 text-sm font-semibold text-teal">LLM Extraction</h3>
      <div className="space-y-1 text-sm">
        {titleEn && (
          <div>
            <span className="text-muted">Title (EN):</span>{" "}
            <span className="font-medium text-bright">{titleEn}</span>
          </div>
        )}
        {titleJa && (
          <div>
            <span className="text-muted">Title (JA):</span>{" "}
            <span className="font-medium text-bright">{titleJa}</span>
          </div>
        )}
        {code && (
          <div>
            <span className="text-muted">Code:</span>{" "}
            <span className="font-mono text-bright">{code}</span>
          </div>
        )}
        <div>
          <span className="text-muted">Confidence:</span>
          <ConfidenceMeter value={confidence} />
        </div>
        {method && (
          <div>
            <span className="text-muted">Method:</span>{" "}
            <span className="text-bright">{method}</span>
          </div>
        )}
      </div>
    </DsoCard>
  );
}
