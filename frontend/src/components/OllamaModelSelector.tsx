import type { OllamaModelInfo } from "../api/types";
import { Select } from "./ui";

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
      return <p className="text-xs text-vermillion">{emptyMessage}</p>;
    }
    return null;
  }

  return (
    <Select
      label={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={className}
      options={[
        { value: "", label: placeholder },
        ...models.map((m) => ({
          value: m.name,
          label:
            showDetails && m.parameter_size
              ? `${m.name} (${m.parameter_size}, ${m.quantization})`
              : m.name,
        })),
      ]}
    />
  );
}
