import { useRef, useState } from "react";
import ReactCrop, {
  centerCrop,
  makeAspectCrop,
  type Crop,
  type PixelCrop,
} from "react-image-crop";
import "react-image-crop/dist/ReactCrop.css";

import { DsoButton } from "./dso";

interface ImageCropperProps {
  imageDataUrl: string;
  originalFileName: string;
  onCropConfirm: (croppedDataUrl: string, croppedFile: File) => void;
  onCancel: () => void;
}

function centerSquareCrop(
  imageWidth: number,
  imageHeight: number,
): PixelCrop {
  const crop = centerCrop(
    makeAspectCrop({ unit: "%", width: 80 }, 1, imageWidth, imageHeight),
    imageWidth,
    imageHeight,
  );
  return { ...crop, unit: "px" };
}

function cropImage(
  image: HTMLImageElement,
  pixelCrop: PixelCrop,
): Promise<{ dataUrl: string; blob: Blob }> {
  const canvas = document.createElement("canvas");
  const scaleX = image.naturalWidth / image.width;
  const scaleY = image.naturalHeight / image.height;
  const cropX = pixelCrop.x * scaleX;
  const cropY = pixelCrop.y * scaleY;
  const cropWidth = pixelCrop.width * scaleX;
  const cropHeight = pixelCrop.height * scaleY;

  canvas.width = cropWidth;
  canvas.height = cropHeight;
  const ctx = canvas.getContext("2d")!;
  ctx.drawImage(
    image,
    cropX,
    cropY,
    cropWidth,
    cropHeight,
    0,
    0,
    cropWidth,
    cropHeight,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Canvas toBlob failed"));
          return;
        }
        const reader = new FileReader();
        reader.onload = () =>
          resolve({ dataUrl: reader.result as string, blob });
        reader.onerror = () => reject(new Error("Failed to read blob"));
        reader.readAsDataURL(blob);
      },
      "image/png",
    );
  });
}

export default function ImageCropper({
  imageDataUrl,
  originalFileName,
  onCropConfirm,
  onCancel,
}: ImageCropperProps) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [crop, setCrop] = useState<Crop>();
  const [completedCrop, setCompletedCrop] = useState<PixelCrop>();
  const [cropping, setCropping] = useState(false);

  function onImageLoad(e: React.SyntheticEvent<HTMLImageElement>) {
    const { width, height } = e.currentTarget;
    const initial = centerSquareCrop(width, height);
    setCrop(initial);
    setCompletedCrop(initial);
  }

  async function handleConfirm() {
    if (!imgRef.current || !completedCrop) return;
    setCropping(true);
    try {
      const { dataUrl, blob } = await cropImage(imgRef.current, completedCrop);
      const ext = originalFileName.split(".").pop() || "png";
      const baseName = originalFileName.replace(/\.[^.]+$/, "");
      const file = new File([blob], `${baseName}_cropped.${ext}`, {
        type: "image/png",
      });
      onCropConfirm(dataUrl, file);
    } finally {
      setCropping(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded border border-highlight/20 bg-lcd p-2">
        <ReactCrop
          crop={crop}
          onChange={(c) => setCrop(c)}
          onComplete={(c) => setCompletedCrop(c)}
        >
          <img
            ref={imgRef}
            src={imageDataUrl}
            alt="Crop target"
            onLoad={onImageLoad}
            className="max-h-96"
          />
        </ReactCrop>
      </div>
      <div className="flex gap-2">
        <DsoButton onClick={handleConfirm} disabled={!completedCrop || cropping}>
          {cropping ? "Cropping..." : "Apply Crop"}
        </DsoButton>
        <DsoButton variant="ghost" onClick={onCancel}>
          Cancel
        </DsoButton>
      </div>
    </div>
  );
}
