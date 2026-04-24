import type { HTMLAttributes, ReactNode } from "react";

interface DsoErrorBannerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
}

export function DsoErrorBanner({
  children,
  className = "",
  ...props
}: DsoErrorBannerProps) {
  return (
    <div
      className={[
        "rounded-lg border border-amber/30 bg-amber/5 p-3 text-sm text-amber",
        "neo-inset",
        className,
      ].join(" ")}
      {...props}
    >
      {children}
    </div>
  );
}
