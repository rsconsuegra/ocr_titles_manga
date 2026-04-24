import { useEffect, useState } from "react";

import type { ParamDescriptor, StepDescriptor } from "../api/client";

interface PreprocessStepCardProps {
  step: StepDescriptor;
  params: Record<string, unknown>;
  enabled: boolean;
  showEnabled?: boolean;
  onParamsChange: (params: Record<string, unknown>) => void;
  onEnabledChange: (enabled: boolean) => void;
}

function ParamInput({
  param,
  value,
  onChange,
}: {
  param: ParamDescriptor;
  value: unknown;
  onChange: (v: unknown) => void;
}) {
  if (param.type === "multiselect" && param.options) {
    const selected = (Array.isArray(value) ? value : param.default ?? []) as string[];
    const toggle = (opt: string) => {
      const next = selected.includes(opt) ? selected.filter((s: string) => s !== opt) : [...selected, opt];
      onChange(next);
    };
    return (
      <div className="flex flex-wrap gap-2">
        {param.options.map((opt) => (
          <label key={opt} className="flex items-center gap-1 text-xs text-bright">
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => toggle(opt)}
              className="h-3.5 w-3.5 rounded border-highlight/40 bg-inset accent-teal"
            />
            <span>{opt}</span>
          </label>
        ))}
      </div>
    );
  }

  if (param.type === "select" && param.options) {
    return (
      <select
        className="rounded border border-highlight/20 bg-inset px-2 py-1 text-sm text-bright focus:border-teal/40 focus:outline-none"
        value={String(value ?? param.default)}
        onChange={(e) => onChange(e.target.value)}
      >
        {param.options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  if (param.type === "boolean") {
    return (
      <input
        type="checkbox"
        checked={Boolean(value ?? param.default)}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-highlight/40 bg-inset accent-teal"
      />
    );
  }

  return (
    <input
      type="number"
      className="w-24 rounded border border-highlight/20 bg-inset px-2 py-1 text-sm text-bright focus:border-teal/40 focus:outline-none"
      value={String(value ?? param.default)}
      step={param.step ?? 1}
      min={param.min}
      max={param.max}
      onChange={(e) => {
        const v = e.target.value;
        onChange(v === "" ? "" : Number(v));
      }}
    />
  );
}

export default function PreprocessStepCard({
  step,
  params,
  enabled,
  showEnabled = true,
  onParamsChange,
  onEnabledChange,
}: PreprocessStepCardProps) {
  const [localParams, setLocalParams] = useState<Record<string, unknown>>(params);

  useEffect(() => {
    setLocalParams(params);
  }, [params]);

  const handleParamChange = (name: string, value: unknown) => {
    const updated = { ...localParams, [name]: value };
    setLocalParams(updated);
    onParamsChange(updated);
  };

  return (
    <div
      className={[
        "rounded-lg border p-3 transition-colors duration-150",
        enabled
          ? "border-teal/30 bg-panel"
          : "border-highlight/20 bg-inset opacity-50",
      ].join(" ")}
    >
      <div className="mb-2 flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-bright">{step.label}</h4>
          <p className="text-xs text-muted">{step.description}</p>
        </div>
        {showEnabled && (
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => onEnabledChange(e.target.checked)}
            className="h-4 w-4 rounded border-highlight/40 bg-inset accent-teal"
          />
        )}
      </div>
      {enabled && step.params.length > 0 && (
        <div className="space-y-2">
          {step.params.map((p) => (
            <div key={p.name} className={p.type === "multiselect" ? "space-y-1" : "flex items-center gap-2"}>
              <label className={p.type === "multiselect" ? "text-xs font-medium text-muted" : "w-24 shrink-0 text-xs font-medium text-muted"}>
                {p.label || p.name}
              </label>
              <ParamInput
                param={p}
                value={localParams[p.name]}
                onChange={(v) => handleParamChange(p.name, v)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
