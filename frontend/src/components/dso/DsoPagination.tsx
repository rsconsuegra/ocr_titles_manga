import type { HTMLAttributes } from "react";

interface DsoPaginationProps extends HTMLAttributes<HTMLDivElement> {
  page: number;
  totalPages: number;
  totalItems: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export function DsoPagination({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
  className = "",
  ...props
}: DsoPaginationProps) {
  const from = totalItems === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, totalItems);

  return (
    <div
      className={`flex items-center justify-between ${className}`}
      {...props}
    >
      <span className="tech-label">
        {from}&ndash;{to} of {totalItems}
      </span>
      <div className="flex gap-2">
        <button
          className="neo-press rounded-lg border border-highlight/20 bg-panel px-3 py-1 text-sm text-bright disabled:opacity-30"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          Prev
        </button>
        <button
          className="neo-press rounded-lg border border-highlight/20 bg-panel px-3 py-1 text-sm text-bright disabled:opacity-30"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
}
