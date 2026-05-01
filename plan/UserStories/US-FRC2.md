# US-FRC2: Use New Card Component

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens)
**Blocks**: US-FRC7 (DSO removal replaces DsoCard with Card), all page stories

---

## Story

> As a user, I want content to be organized in clean white cards with subtle shadows so that information is well-grouped and easy to scan.

---

## Scope

### In Scope
- New `Card.tsx` with optional accent, padding, hover props
- `Card.Header` sub-component with title + action slot

### Out of Scope
- Replacing DsoCard in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Card.tsx` (new)

```tsx
import type { ReactNode } from "react";

type CardAccent = "indigo" | "vermillion" | "success" | "warning";
type CardPadding = "sm" | "md" | "lg";

interface CardProps {
  children: ReactNode;
  accent?: CardAccent;
  padding?: CardPadding;
  hover?: boolean;
  className?: string;
}

const accentClasses: Record<CardAccent, string> = {
  indigo: "border-t-3 border-t-indigo",
  vermillion: "border-t-3 border-t-vermillion",
  success: "border-t-3 border-t-success",
  warning: "border-t-3 border-t-warning",
};

const paddingClasses: Record<CardPadding, string> = {
  sm: "p-3",
  md: "p-5",
  lg: "p-6",
};

export default function Card({
  children,
  accent,
  padding = "md",
  hover = false,
  className = "",
}: CardProps) {
  return (
    <div
      className={`
        bg-snow rounded-lg shadow-sm border border-linen
        ${accent ? accentClasses[accent] : ""}
        ${paddingClasses[padding]}
        ${hover ? "hover:shadow-md transition-shadow" : ""}
        ${className}
      `}
    >
      {children}
    </div>
  );
}

function CardHeader({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      {children}
    </div>
  );
}

Card.Header = CardHeader;
```

---

## Acceptance Criteria

- [ ] Card renders bg-snow, rounded-lg, shadow-sm, border border-linen
- [ ] `accent` prop: adds 3px top border in indigo/vermillion/success/warning
- [ ] `padding` prop: sm=p-3, md=p-5 (default), lg=p-6
- [ ] `hover` prop: enables shadow-md on hover with transition
- [ ] `Card.Header` sub-component renders flex row with title (font-display, text-lg, font-semibold, text-ink)
- [ ] `Card.Header` accepts optional `children` for action slot on right
- [ ] `className` prop merges with base classes

---

## Validation

1. Render Card with each accent color — verify colored top border
2. Render Card with hover=true — verify shadow increases on mouse-over
3. Render Card.Header with title + action button — verify flex layout
