import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "amber" | "danger" | "ghost";

interface DsoButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-gradient-to-b from-teal to-teal-dim text-white shadow-[0_0_12px_rgba(56,178,172,0.25)] hover:shadow-[0_0_18px_rgba(56,178,172,0.4)]",
  secondary: "bg-panel text-bright neo-press",
  amber: "bg-amber text-chassis font-bold neo-press hover:bg-amber-dim",
  danger:
    "bg-red-900/60 text-red-300 neo-press hover:bg-red-900/80 border border-red-800/40",
  ghost: "text-muted hover:text-bright neo-press",
};

export const DsoButton = forwardRef<HTMLButtonElement, DsoButtonProps>(
  ({ variant = "primary", className = "", disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={[
          "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all duration-150",
          "disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none",
          variants[variant],
          variant === "primary" ? "active:translate-y-[1px] active:scale-[0.98]" : "",
          className,
        ]
          .filter(Boolean)
          .join(" ")}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  },
);

DsoButton.displayName = "DsoButton";
