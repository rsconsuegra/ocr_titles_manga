import { useRef, useState } from "react";

import { useFileReader } from "../hooks/useFileReader";
import { DsoButton } from "./dso";
import ImageCropper from "./ImageCropper";

interface SingleImageUploadProps {
  imageDataUrl: string;
  fileName?: string;
  showPaste?: boolean;
  onImageChange: (dataUrl: string, file: File) => void;
}

export default function SingleImageUpload({
  imageDataUrl,
  fileName = "",
  showPaste = false,
  onImageChange,
}: SingleImageUploadProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const readFile = useFileReader();
  const [isCropping, setIsCropping] = useState(false);
  const [originalDataUrl, setOriginalDataUrl] = useState("");
  const [originalFile, setOriginalFile] = useState<File | null>(null);

  async function handlePaste() {
    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        const imageType = item.types?.find((t) => t.startsWith("image/"));
        if (imageType) {
          const blob = await item.getType(imageType);
          const file = new File([blob], "pasted.png", { type: imageType });
          const dataUrl = await readFile(file);
          onImageChange(dataUrl, file);
          setIsCropping(false);
          setOriginalDataUrl("");
          setOriginalFile(null);
          return;
        }
      }
    } catch {
      // clipboard access denied
    }
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const dataUrl = await readFile(file);
    onImageChange(dataUrl, file);
    setIsCropping(false);
    setOriginalDataUrl("");
    setOriginalFile(null);
  }

  function handleStartCrop() {
    setOriginalDataUrl(imageDataUrl);
    if (!originalFile) {
      setOriginalFile(
        new File([], fileName || "image.png", { type: "image/png" }),
      );
    }
    setIsCropping(true);
  }

  function handleCropConfirm(croppedDataUrl: string, croppedFile: File) {
    onImageChange(croppedDataUrl, croppedFile);
    setIsCropping(false);
  }

  function handleCropCancel() {
    setIsCropping(false);
  }

  function handleResetCrop() {
    if (originalDataUrl && originalFile) {
      onImageChange(originalDataUrl, originalFile);
      setOriginalDataUrl("");
      setOriginalFile(null);
    }
  }

  return (
    <div>
      <p className="tech-label mb-1">Image</p>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
      <div className="flex flex-wrap gap-2">
        <DsoButton variant="secondary" onClick={() => fileRef.current?.click()}>
          {imageDataUrl ? "Change Image" : "Upload Image"}
        </DsoButton>
        {showPaste && (
          <DsoButton variant="secondary" onClick={handlePaste}>
            Paste
          </DsoButton>
        )}
        {imageDataUrl && !isCropping && (
          <DsoButton variant="ghost" onClick={handleStartCrop}>
            Crop
          </DsoButton>
        )}
        {originalDataUrl && !isCropping && (
          <DsoButton variant="ghost" onClick={handleResetCrop}>
            Reset Crop
          </DsoButton>
        )}
      </div>
      {isCropping ? (
        <div className="mt-2">
          <ImageCropper
            imageDataUrl={imageDataUrl}
            originalFileName={fileName}
            onCropConfirm={handleCropConfirm}
            onCancel={handleCropCancel}
          />
        </div>
      ) : (
        imageDataUrl && (
          <img
            src={imageDataUrl}
            alt="Preview"
            className="mt-2 max-h-48 rounded border border-highlight/20"
          />
        )
      )}
    </div>
  );
}
