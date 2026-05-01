import type { PipelineStepResult } from "../api/client";

interface PipelineFilmstripProps {
  steps: PipelineStepResult[];
}

export default function PipelineFilmstrip({ steps }: PipelineFilmstripProps) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {steps.map((step) => (
        <div key={step.step_name} className="w-[200px] shrink-0">
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-ink">{step.step_name}</span>
            {step.enabled ? (
              step.success ? (
                <div className="flex items-center gap-1">
                  <span className="size-1.5 inline-block rounded-full bg-indigo" />
                  <span className="text-xs text-indigo">OK</span>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <span className="size-1.5 inline-block rounded-full bg-vermillion" />
                  <span className="text-xs text-vermillion">FAIL</span>
                </div>
              )
            ) : (
              <span className="text-xs text-sand">OFF</span>
            )}
          </div>
          <div className="h-[150px] w-[200px] overflow-hidden rounded border border-linen bg-cream">
            {step.enabled && step.image ? (
              <img src={step.image} alt={step.step_name} className="h-full w-full object-contain" />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-sand">
                {step.enabled ? "No image" : "Disabled"}
              </div>
            )}
          </div>
          <div className="mt-0.5 text-right text-xs text-sand">{step.processing_time_ms}ms</div>
        </div>
      ))}
    </div>
  );
}
