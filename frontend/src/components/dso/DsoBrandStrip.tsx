import type { HTMLAttributes, ReactNode } from "react";

interface DsoBrandStripProps extends HTMLAttributes<HTMLElement> {
  variant: "header" | "footer";
  children?: ReactNode;
}

export function DsoBrandStrip({
  variant,
  children,
  className = "",
  ...props
}: DsoBrandStripProps) {
  const Tag = variant === "header" ? "nav" : "footer";

  return (
    <Tag
      className={[
        "relative flex items-center",
        "bg-gradient-to-r from-panel via-panel-light to-panel",
        variant === "header" ? "px-4 py-3" : "px-4 py-2",
        className,
      ].join(" ")}
      {...props}
    >
      <DsoScrew className="absolute left-2 top-2" />
      <DsoScrew className="absolute right-2 top-2" />
      {children}
      {variant === "header" && (
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-teal/20 to-transparent" />
      )}
    </Tag>
  );
}

export function DsoScrew({
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={[
        "inline-block h-3 w-3 rounded-full bg-panel-light",
        "shadow-[inset_2px_2px_4px_rgba(10,12,16,0.6),inset_-1px_-1px_3px_rgba(55,63,75,0.3)]",
        "relative",
        className,
      ].join(" ")}
      {...props}
    >
      <span className="absolute left-1/2 top-1/2 h-px w-1.5 -translate-x-1/2 -translate-y-1/2 bg-highlight/40" />
    </span>
  );
}

export function DsoVentGrille({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`flex flex-col gap-1.5 ${className}`}
      {...props}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-0.5 w-6 rounded-full bg-panel-light shadow-[inset_1px_1px_2px_rgba(10,12,16,0.6),inset_-1px_-1px_2px_rgba(55,63,75,0.2)]"
        />
      ))}
    </div>
  );
}
