import type { HTMLAttributes } from "react";

interface DsoProgressBarProps extends HTMLAttributes<HTMLDivElement> {
  value: number;
  max?: number;
  colorClass?: string;
  label?: string;
  showPercent?: boolean;
  size?: "sm" | "md";
}

export function DsoProgressBar({
  value,
  max = 1,
  colorClass,
  label,
  showPercent = false,
  size = "sm",
  className = "",
  ...props
}: DsoProgressBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const resolvedColor =
    colorClass ??
    (pct >= 70
      ? "bg-teal"
      : pct >= 30
        ? "bg-amber"
        : "bg-red-500");

  const height = size === "sm" ? "h-2" : "h-3";

  return (
    <div className={`flex items-center gap-2 ${className}`} {...props}>
      {label && <span className="text-xs text-muted shrink-0">{label}</span>}
      <div
        className={`${height} w-full rounded-full bg-surface-dark overflow-hidden`}
      >
        <div
          className={`${height} rounded-full transition-all duration-300 ${resolvedColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showPercent && (
        <span className="text-xs text-muted tabular-nums w-10 text-right">
          {Math.round(pct)}%
        </span>
      )}
    </div>
  );
}
