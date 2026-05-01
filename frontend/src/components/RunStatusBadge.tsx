import { Badge } from "./ui";

const VARIANT_MAP: Record<
  string,
  "pending" | "processing" | "completed" | "failed" | "cancelled" | "default"
> = {
  pending: "pending",
  processing: "processing",
  completed: "completed",
  failed: "failed",
  cancelled: "cancelled",
};

export default function RunStatusBadge({ status }: { status: string }) {
  const mapped = VARIANT_MAP[status] ?? "default";
  return <Badge status={mapped}>{status}</Badge>;
}
