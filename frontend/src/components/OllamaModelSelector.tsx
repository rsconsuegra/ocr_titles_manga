import type { OllamaModelInfo } from "../api/types";
import { DsoSelect } from "./dso";

interface OllamaModelSelectorProps {
  label: string;
  models: OllamaModelInfo[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  showDetails?: boolean;
  emptyMessage?: string;
  className?: string;
}

export default function OllamaModelSelector({
  label,
  models,
  value,
  onChange,
  placeholder = "Select a model...",
  showDetails = false,
  emptyMessage,
  className,
}: OllamaModelSelectorProps) {
  if (models.length === 0) {
    if (emptyMessage) {
      return <p className="text-xs text-amber">{emptyMessage}</p>;
    }
    return null;
  }

  return (
    <DsoSelect
      label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
    >
      <option value="">{placeholder}</option>
      {models.map((m) => (
        <option key={m.name} value={m.name}>
          {showDetails && m.parameter_size ? `${m.name} (${m.parameter_size}, ${m.quantization})` : m.name}
        </option>
      ))}
    </DsoSelect>
  );
}
