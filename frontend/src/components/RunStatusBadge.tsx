import { DsoBadge } from "./dso";

const VARIANT_MAP: Record<string, "pending" | "processing" | "completed" | "failed" | "cancelled" | "default"> = {
  pending: "pending",
  processing: "processing",
  completed: "completed",
  failed: "failed",
  cancelled: "cancelled",
};

export default function RunStatusBadge({ status }: { status: string }) {
  const variant = VARIANT_MAP[status] ?? "default";
  return <DsoBadge variant={variant}>{status}</DsoBadge>;
}
