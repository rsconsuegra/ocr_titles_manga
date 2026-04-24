import { type ChangeEvent, type DragEvent, useCallback, useState } from "react";

import { DsoErrorBanner } from "./dso";

const ALLOWED = new Set([".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"]);
const MAX_FILES = 10;

interface Props {
  onFilesSelected: (files: File[]) => void;
  maxFiles?: number;
}

export default function ImageUploader({ onFilesSelected, maxFiles = MAX_FILES }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validate = useCallback(
    (incoming: File[]): File[] => {
      const errs: string[] = [];
      const valid: File[] = [];
      for (const f of incoming) {
        const ext = "." + f.name.split(".").pop()?.toLowerCase();
        if (!ALLOWED.has(ext)) {
          errs.push(`Invalid format: ${f.name}`);
          continue;
        }
        valid.push(f);
      }
      if (files.length + valid.length > maxFiles) {
        errs.push(`Maximum ${maxFiles} files`);
        return [];
      }
      setErrors(errs);
      return valid;
    },
    [files.length, maxFiles],
  );

  const addFiles = useCallback(
    (incoming: File[]) => {
      const valid = validate(incoming);
      if (valid.length === 0) return;
      const next = [...files, ...valid];
      setFiles(next);
      onFilesSelected(next);
    },
    [files, validate, onFilesSelected],
  );

  const removeFile = (idx: number) => {
    const next = files.filter((_, i) => i !== idx);
    setFiles(next);
    onFilesSelected(next);
    setErrors([]);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    addFiles(Array.from(e.dataTransfer.files));
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) addFiles(Array.from(e.target.files));
    e.target.value = "";
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        className={[
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-all duration-150",
          dragActive
            ? "border-teal/60 bg-teal/5 shadow-[inset_0_0_20px_rgba(56,178,172,0.08)]"
            : "border-highlight/30 bg-inset neo-inset",
        ].join(" ")}
        onClick={() => document.getElementById("file-picker")?.click()}
      >
        <svg className="mb-2 h-10 w-10 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <p className="text-sm text-muted">Drop manga images here or click to browse</p>
        <input id="file-picker" type="file" multiple accept=".png,.jpg,.jpeg,.webp,.tiff,.tif,.bmp" className="hidden" onChange={onChange} />
      </div>

      {errors.length > 0 && (
        <DsoErrorBanner className="mt-2">
          {errors.map((e, i) => (
            <div key={i}>{e}</div>
          ))}
        </DsoErrorBanner>
      )}

      {files.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {files.map((f, i) => (
            <div key={i} className="group relative neo-inset p-2">
              <img
                src={URL.createObjectURL(f)}
                alt={f.name}
                className="mb-1 h-24 w-full rounded object-cover"
              />
              <p className="truncate text-xs text-bright">{f.name}</p>
              <p className="text-xs text-muted">{(f.size / 1024).toFixed(0)} KB</p>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  removeFile(i);
                }}
                className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-amber text-xs text-chassis opacity-0 transition-opacity group-hover:opacity-100"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
