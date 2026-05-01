interface ImageCompareProps {
  beforeSrc: string;
  afterSrc: string;
  beforeLabel?: string;
  afterLabel?: string;
}

export default function ImageCompare({
  beforeSrc,
  afterSrc,
  beforeLabel = "Before",
  afterLabel = "After",
}: ImageCompareProps) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="overflow-hidden rounded border border-linen">
        <div className="label-text bg-linen/50 px-2 py-1">{beforeLabel}</div>
        <img src={beforeSrc} alt={beforeLabel} className="block w-full" draggable={false} />
      </div>
      <div className="overflow-hidden rounded border border-linen">
        <div className="label-text bg-linen/50 px-2 py-1">{afterLabel}</div>
        <img src={afterSrc} alt={afterLabel} className="block w-full" draggable={false} />
      </div>
    </div>
  );
}
