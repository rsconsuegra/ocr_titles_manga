import { ProgressBar } from "./ui";

export default function ConfidenceMeter({ value }: { value: number; label?: string }) {
  return <ProgressBar value={value * 100} showLabel />;
}
