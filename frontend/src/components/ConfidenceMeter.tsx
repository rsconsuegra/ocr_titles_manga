import { DsoProgressBar } from "./dso";

function getColor(value: number): string | undefined {
  if (value < 0.3) return "bg-red-500";
  if (value < 0.7) return "bg-amber";
  return undefined;
}

export default function ConfidenceMeter({ value, label }: { value: number; label?: string }) {
  return (
    <DsoProgressBar
      value={value}
      max={1}
      colorClass={getColor(value)}
      label={label}
      showPercent
    />
  );
}
