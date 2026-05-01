type ProgressSize = "sm" | "md";

interface ProgressBarProps {
  value: number;
  size?: ProgressSize;
  showLabel?: boolean;
  className?: string;
}

function getColor(value: number): string {
  if (value >= 70) return "bg-success";
  if (value >= 30) return "bg-warning";
  return "bg-error";
}

export default function ProgressBar({
  value,
  size = "md",
  showLabel = false,
  className = "",
}: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-xs font-body text-sand">Progress</span>
          <span className="text-xs font-body text-charcoal">{Math.round(clamped)}%</span>
        </div>
      )}
      <div className={`w-full rounded-full bg-linen ${size === "sm" ? "h-1.5" : "h-2.5"}`}>
        <div
          className={`h-full rounded-full transition-all duration-300 ${getColor(clamped)}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
