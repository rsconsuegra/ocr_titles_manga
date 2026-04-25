import type { HTMLAttributes, ReactNode } from "react";

type BadgeVariant = "pending" | "processing" | "completed" | "failed" | "cancelled" | "default" | "review";

interface DsoBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  led?: boolean;
  children: ReactNode;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; led: string }> = {
  pending: { bg: "bg-amber/10 border border-amber/20", text: "text-amber", led: "led-amber" },
  processing: { bg: "bg-amber/10 border border-amber/20", text: "text-amber", led: "led-active" },
  completed: { bg: "bg-teal/15 border border-teal/30", text: "text-teal", led: "led-active" },
  failed: { bg: "bg-red-900/30 border border-red-800/30", text: "text-red-400", led: "led-amber" },
  cancelled: { bg: "bg-inset border border-highlight/20", text: "text-muted", led: "led-off" },
  default: { bg: "bg-inset border border-highlight/20", text: "text-muted", led: "led-off" },
  review: { bg: "bg-amber/10 border border-amber/20", text: "text-amber", led: "led-amber" },
};

export function DsoBadge({
  variant = "default",
  led = true,
  className = "",
  children,
  ...props
}: DsoBadgeProps) {
  const style = variantStyles[variant];
  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        style.bg,
        style.text,
        className,
      ].join(" ")}
      {...props}
    >
      {led && <span className={`led ${style.led}`} />}
      {children}
    </span>
  );
}
