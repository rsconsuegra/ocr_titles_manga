import type { HTMLAttributes, ReactNode } from "react";

interface DsoCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "flat" | "inset" | "lcd";
  children: ReactNode;
}

export function DsoCard({
  variant = "flat",
  className = "",
  children,
  ...props
}: DsoCardProps) {
  const base = {
    flat: "neo-panel p-4",
    inset: "neo-deep-inset p-4",
    lcd: "lcd-screen lcd-graticule p-4",
  }[variant];

  return (
    <div className={`${base} ${className}`} {...props}>
      {children}
    </div>
  );
}
