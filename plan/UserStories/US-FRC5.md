# US-FRC5: Use New Table Component

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens)
**Blocks**: US-FRC7 (DSO removal replaces DsoTable), page stories with tables

---

## Story

> As a user, I want data displayed in clean tables with clear headers, hoverable rows, and consistent styling so that I can quickly scan and compare information.

---

## Scope

### In Scope
- New generic typed `Table.tsx` with column definitions
- Header styling, row hover, click handler, empty state

### Out of Scope
- Replacing DsoTable in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Table.tsx` (new)

```tsx
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

export default function Table<T extends Record<string, unknown>>({
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
              className={`
                bg-snow border-b border-linen last:border-b-0
                ${onRowClick ? "cursor-pointer hover:bg-cream/50" : ""}
                transition-colors
              `}
            >
              {columns.map((col) => (
                <td key={String(col.key)} className={`px-4 py-3 text-sm font-body text-charcoal ${col.className || ""}`}>
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
```

---

## Acceptance Criteria

- [ ] Generic typed `<T>` component with `Column<T>` definitions
- [ ] Column: `key` (keyof T), `header` (string), optional `render` function, optional `className`
- [ ] Header row: bg-cream, label-text style, px-4 py-3
- [ ] Data rows: bg-snow, border-b border-linen, last row no bottom border
- [ ] Hover: bg-cream/50 (only when `onRowClick` is provided)
- [ ] Clickable rows: cursor-pointer when `onRowClick` provided
- [ ] Empty state: centered text showing `emptyMessage` when data is empty
- [ ] Wrapped in overflow-x-auto for horizontal scroll on narrow screens
- [ ] Outer container: rounded-lg, border border-linen

---

## Validation

1. Render Table with 3 columns and 5 rows — verify headers, row styling
2. Hover a row with onRowClick — verify bg-cream/50 highlight
3. Pass empty data array — verify empty message displays
4. Render a column with custom render function — verify custom output
