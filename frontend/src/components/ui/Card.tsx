import type { ReactNode } from "react";

type CardAccent = "indigo" | "vermillion" | "success" | "warning";
type CardPadding = "sm" | "md" | "lg";

interface CardProps {
  children: ReactNode;
  accent?: CardAccent;
  padding?: CardPadding;
  hover?: boolean;
  className?: string;
  onClick?: () => void;
}

const accentClasses: Record<CardAccent, string> = {
  indigo: "border-t-3 border-t-indigo",
  vermillion: "border-t-3 border-t-vermillion",
  success: "border-t-3 border-t-success",
  warning: "border-t-3 border-t-warning",
};

const paddingClasses: Record<CardPadding, string> = {
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

export default function Card({
  children,
  accent,
  padding = "md",
  hover = false,
  className = "",
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      className={`
        bg-snow rounded-lg shadow-sm border border-linen
        ${accent ? accentClasses[accent] : ""}
        ${paddingClasses[padding]}
        ${hover ? "hover:shadow-md transition-shadow" : ""}
        ${onClick ? "cursor-pointer" : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

function CardHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      {children}
    </div>
  );
}

Card.Header = CardHeader;
