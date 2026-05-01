type BadgeStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "review"
  | "default";

type BadgeSize = "sm" | "md";

interface BadgeProps {
  status: BadgeStatus;
  size?: BadgeSize;
  className?: string;
  children?: React.ReactNode;
}

const statusClasses: Record<BadgeStatus, string> = {
  pending: "bg-stone/20 text-stone",
  processing: "bg-indigo-pale text-indigo animate-pulse",
  completed: "bg-success/10 text-success",
  failed: "bg-error/10 text-error",
  cancelled: "bg-stone/20 text-stone",
  review: "bg-warning/10 text-warning",
  default: "bg-linen text-sand",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export default function Badge({ status, size = "md", className = "", children }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center rounded-full font-medium font-body
        ${statusClasses[status]}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {children ?? status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
