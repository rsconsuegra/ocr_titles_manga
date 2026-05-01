# US-FRC6: Use New Pagination, ProgressBar, ErrorBanner, EmptyState Components

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens), US-FRC1 (Button for Pagination)
**Blocks**: US-FRC7 (DSO removal), page stories

---

## Story

> As a user, I want consistent pagination controls, progress indicators, error displays, and empty states across all pages so that the interface feels unified and predictable.

---

## Scope

### In Scope
- `Pagination.tsx` — prev/next with counter
- `ProgressBar.tsx` — color-coded, 2 sizes
- `ErrorBanner.tsx` — red-bordered error display with dismiss
- `EmptyState.tsx` — icon + title + description + action button

### Out of Scope
- Replacing DSO equivalents in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Pagination.tsx` (new)

```tsx
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
```

### 2. `frontend/src/components/ui/ProgressBar.tsx` (new)

```tsx
type ProgressSize = "sm" | "md";

interface ProgressBarProps {
  value: number;
  size?: ProgressSize;
  showLabel?: boolean;
  className?: string;
}

function getColor(value: number): string {
  if (value >= 70) return "bg-success";
  if (value >= 30) return "bg-warning";
  return "bg-error";
}

export default function ProgressBar({ value, size = "md", showLabel = false, className = "" }: ProgressBarProps) {
  const clamped = Math.min(100, Math.max(0, value));

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between mb-1">
          <span className="text-xs font-body text-sand">Progress</span>
          <span className="text-xs font-body text-charcoal">{Math.round(clamped)}%</span>
        </div>
      )}
      <div className={`w-full rounded-full bg-linen ${size === "sm" ? "h-1.5" : "h-2.5"}`}>
        <div
          className={`rounded-full transition-all duration-300 ${getColor(clamped)}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
```

### 3. `frontend/src/components/ui/ErrorBanner.tsx` (new)

```tsx
import type { ReactNode } from "react";

interface ErrorBannerProps {
  message: string;
  onDismiss?: () => void;
  children?: ReactNode;
}

export default function ErrorBanner({ message, onDismiss, children }: ErrorBannerProps) {
  return (
    <div className="bg-error/5 border-l-4 border-error rounded-md px-4 py-3">
      <div className="flex items-start justify-between">
        <p className="text-error text-sm font-body">{message}</p>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-error/60 hover:text-error ml-4 text-lg leading-none"
          >
            ×
          </button>
        )}
      </div>
      {children}
    </div>
  );
}
```

### 4. `frontend/src/components/ui/EmptyState.tsx` (new)

```tsx
import type { ReactNode } from "react";
import Button from "./Button";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export default function EmptyState({ icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="mb-4 text-sand">{icon}</div>}
      <h3 className="font-display text-lg font-semibold text-ink mb-2">{title}</h3>
      {description && <p className="text-sand font-body text-sm max-w-md mb-6">{description}</p>}
      {actionLabel && onAction && (
        <Button variant="primary" onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  );
}
```

---

## Acceptance Criteria

**Pagination:**
- [ ] Prev/Next ghost buttons with disabled state at boundaries
- [ ] "X–Y of Z" counter in sand text
- [ ] `offset=0` → Prev disabled; `end >= total` → Next disabled

**ProgressBar:**
- [ ] Rounded-full track bg-linen
- [ ] Fill color: success (>=70%), warning (>=30%), error (<30%)
- [ ] Two sizes: sm (h-1.5), md (h-2.5)
- [ ] Optional percentage label with `showLabel`
- [ ] Value clamped to 0-100

**ErrorBanner:**
- [ ] bg-error/5, left border-l-4 border-error, text-error
- [ ] Rounded-md, px-4 py-3
- [ ] Optional dismiss X button via `onDismiss`

**EmptyState:**
- [ ] Centered layout with optional icon, title (font-display), description (sand)
- [ ] Optional action Button with `actionLabel` and `onAction`
- [ ] py-16 for generous vertical spacing

---

## Validation

1. Pagination: render with offset=20, limit=10, total=50 — shows "21–30 of 50"
2. ProgressBar: render at 80%, 50%, 10% — verify green, amber, red fills
3. ErrorBanner: render with message — verify red left border
4. EmptyState: render with icon, title, description, action — verify centered layout
