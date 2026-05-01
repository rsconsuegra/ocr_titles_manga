import { useRef, useState } from "react";

import { useFileReader } from "../hooks/useFileReader";
import ImageCropper from "./ImageCropper";
import { Button } from "./ui";

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
      setOriginalFile(new File([], fileName || "image.png", { type: "image/png" }));
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
      <span className="label-text mb-2 block">Image</span>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        className="hidden"
      />
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" onClick={() => fileRef.current?.click()}>
          {imageDataUrl ? "Change Image" : "Upload Image"}
        </Button>
        {showPaste && (
          <Button variant="secondary" onClick={handlePaste}>
            Paste
          </Button>
        )}
        {imageDataUrl && !isCropping && (
          <Button variant="ghost" onClick={handleStartCrop}>
            Crop
          </Button>
        )}
        {originalDataUrl && !isCropping && (
          <Button variant="ghost" onClick={handleResetCrop}>
            Reset Crop
          </Button>
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
            className="mt-2 max-h-48 rounded border border-linen"
          />
        )
      )}
    </div>
  );
}
