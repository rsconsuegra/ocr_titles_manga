import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

interface Column<T> {
  header: string;
  render: (row: T, index: number) => ReactNode;
  className?: string;
}

interface DsoTableProps<T> extends Omit<HTMLAttributes<HTMLTableElement>, "children"> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T, index: number) => void;
  keyFn: (row: T, index: number) => string;
  emptyMessage?: string;
}

export function DsoTable<T>({
  columns,
  data,
  onRowClick,
  keyFn,
  emptyMessage = "No data",
  className = "",
  ...props
}: DsoTableProps<T>) {
  return (
    <div className="neo-inset overflow-hidden">
      <table className={`w-full text-left text-sm ${className}`} {...props}>
        <thead>
          <tr className="border-b border-highlight/20">
            {columns.map((col, i) => (
              <DsoTh key={i} className={col.className}>
                {col.header}
              </DsoTh>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-muted"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, index) => (
              <tr
                key={keyFn(row, index)}
                className={[
                  "border-b border-highlight/10 transition-colors duration-100",
                  onRowClick
                    ? "cursor-pointer hover:bg-teal/5"
                    : "",
                ].join(" ")}
                onClick={() => onRowClick?.(row, index)}
              >
                {columns.map((col, i) => (
                  <DsoTd key={i} className={col.className}>
                    {col.render(row, index)}
                  </DsoTd>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function DsoTh({
  className = "",
  children,
  ...props
}: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={`px-4 py-3 tech-label text-muted ${className}`}
      {...props}
    >
      {children}
    </th>
  );
}

export function DsoTd({
  className = "",
  children,
  ...props
}: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={`px-4 py-3 text-bright/90 ${className}`} {...props}>
      {children}
    </td>
  );
}
