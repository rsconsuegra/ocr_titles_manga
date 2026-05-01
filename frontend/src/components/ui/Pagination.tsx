import Button from "./Button";

interface PaginationProps {
  offset: number;
  limit: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}

export default function Pagination({ offset, limit, total, onPrev, onNext }: PaginationProps) {
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);
  const hasPrev = offset > 0;
  const hasNext = end < total;

  return (
    <div className="flex items-center justify-between py-3">
      <span className="text-sm text-sand font-body">
        {start}–{end} of {total}
      </span>
      <div className="flex gap-2">
        <Button variant="ghost" size="sm" onClick={onPrev} disabled={!hasPrev}>
          Previous
        </Button>
        <Button variant="ghost" size="sm" onClick={onNext} disabled={!hasNext}>
          Next
        </Button>
      </div>
    </div>
  );
}
