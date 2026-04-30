import { useId } from "react";

interface PromptSettingsPanelProps {
  systemPrompt: string;
  onSystemPromptChange: (v: string) => void;
  userPrompt: string;
  onUserPromptChange: (v: string) => void;
  temperature: number;
  onTemperatureChange: (v: number) => void;
  maxOcrChars: number;
  onMaxOcrCharsChange: (v: number) => void;
  showToggle: boolean;
  isOpen: boolean;
  onToggle: () => void;
  size?: "sm" | "md";
}

export default function PromptSettingsPanel({
  systemPrompt,
  onSystemPromptChange,
  userPrompt,
  onUserPromptChange,
  temperature,
  onTemperatureChange,
  maxOcrChars,
  onMaxOcrCharsChange,
  showToggle,
  isOpen,
  onToggle,
  size = "sm",
}: PromptSettingsPanelProps) {
  const uid = useId();
  const textSize = size === "sm" ? "text-xs" : "text-sm";
  const inputClass = `w-full rounded border border-highlight/20 bg-inset p-2 ${textSize} text-bright placeholder:text-muted/50 focus:border-teal/50 focus:outline-none`;
  const numInputClass = `w-24 rounded border border-highlight/20 bg-inset p-2 ${textSize} text-bright focus:border-teal/50 focus:outline-none`;
  const numInputClassWide = `w-32 rounded border border-highlight/20 bg-inset p-2 ${textSize} text-bright placeholder:text-muted/50 focus:border-teal/50 focus:outline-none`;

  const content = (
    <div className="space-y-2 rounded border border-highlight/20 p-3">
      <div>
        <label htmlFor={`${uid}-sys`} className="mb-1 block text-xs text-muted">System Prompt</label>
        {size === "md" ? (
          <textarea
            id={`${uid}-sys`}
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            placeholder="Leave empty to use default prompt"
            rows={4}
            className={inputClass}
          />
        ) : (
          <textarea
            id={`${uid}-sys`}
            value={systemPrompt}
            onChange={(e) => onSystemPromptChange(e.target.value)}
            placeholder="Default prompt"
            rows={3}
            className={inputClass}
          />
        )}
      </div>
      <div>
        <label htmlFor={`${uid}-usr`} className="mb-1 block text-xs text-muted">User Prompt Template</label>
        <textarea
          id={`${uid}-usr`}
          value={userPrompt}
          onChange={(e) => onUserPromptChange(e.target.value)}
          placeholder="{ocr_text}"
          rows={size === "md" ? 3 : 2}
          className={inputClass}
        />
        <p className="mt-1 text-xs text-muted">Available: {"{ocr_text}"}</p>
      </div>
      <div>
        <label htmlFor={`${uid}-temp`} className="mb-1 block text-xs text-muted">Temperature</label>
        <input
          id={`${uid}-temp`}
          type="number"
          value={temperature}
          onChange={(e) => onTemperatureChange(parseFloat(e.target.value) || 0.1)}
          min={0}
          max={2}
          step={0.1}
          className={numInputClass}
        />
      </div>
      <div>
        <label htmlFor={`${uid}-max`} className="mb-1 block text-xs text-muted">Max OCR Characters</label>
        <input
          id={`${uid}-max`}
          type="number"
          value={maxOcrChars || ""}
          onChange={(e) => onMaxOcrCharsChange(parseInt(e.target.value) || 0)}
          min={0}
          placeholder="0 = no limit"
          className={size === "md" ? numInputClassWide : numInputClass}
        />
      </div>
    </div>
  );

  if (!showToggle) {
    return content;
  }

  return (
    <div className="space-y-2">
      <button
        type="button"
        className="text-xs text-muted hover:text-teal"
        onClick={onToggle}
      >
        {isOpen ? "▸ Hide" : "▾ Show"} Prompt Settings
      </button>
      {isOpen && content}
    </div>
  );
}
