import type { ReactNode } from "react";

export interface Column<T> {
  key: keyof T;
  header: string;
  render?: (row: T) => ReactNode;
  className?: string;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

export default function Table<T extends object>({
  columns,
  data,
  onRowClick,
  emptyMessage = "No data available",
}: TableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-sand font-body">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-linen">
      <table className="w-full">
        <thead>
          <tr className="bg-cream">
            {columns.map((col) => (
              <th
                key={String(col.key)}
                className={`text-left px-4 py-3 label-text ${col.className || ""}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={i}
              onClick={() => onRowClick?.(row)}
              tabIndex={onRowClick ? 0 : undefined}
              onKeyDown={(e) => {
                if (onRowClick && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  onRowClick(row);
                }
              }}
              className={`
                bg-snow border-b border-linen last:border-b-0
                ${onRowClick ? "cursor-pointer hover:bg-cream/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-indigo/20" : ""}
                transition-colors
              `}
            >
              {columns.map((col) => (
                <td
                  key={String(col.key)}
                  className={`px-4 py-3 text-sm font-body text-charcoal ${col.className || ""}`}
                >
                  {col.render ? col.render(row) : String(row[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
