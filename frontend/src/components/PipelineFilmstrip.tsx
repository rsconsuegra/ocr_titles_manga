import type { PipelineStepResult } from "../api/client";

interface PipelineFilmstripProps {
  steps: PipelineStepResult[];
}

export default function PipelineFilmstrip({ steps }: PipelineFilmstripProps) {
  return (
    <div className="flex gap-3 overflow-x-auto pb-2">
      {steps.map((step) => (
        <div key={step.step_name} className="shrink-0" style={{ width: 200 }}>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-bright">{step.step_name}</span>
            {step.enabled ? (
              step.success ? (
                <div className="flex items-center gap-1">
                  <span className="led led-active" style={{ width: 6, height: 6 }} />
                  <span className="text-xs text-teal">OK</span>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <span className="led led-amber" style={{ width: 6, height: 6 }} />
                  <span className="text-xs text-amber">FAIL</span>
                </div>
              )
            ) : (
              <span className="text-xs text-muted">OFF</span>
            )}
          </div>
          <div className="h-[150px] w-[200px] overflow-hidden rounded bg-lcd neo-inset">
            {step.enabled && step.image ? (
              <img
                src={step.image}
                alt={step.step_name}
                className="h-full w-full object-contain"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-xs text-muted">
                {step.enabled ? "No image" : "Disabled"}
              </div>
            )}
          </div>
          <div className="mt-0.5 text-right text-xs text-muted">
            {step.processing_time_ms}ms
          </div>
        </div>
      ))}
    </div>
  );
}
