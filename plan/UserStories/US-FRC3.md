# US-FRC3: Use New Badge Component

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens)
**Blocks**: US-FRC7 (DSO removal replaces DsoBadge with Badge), RunStatusBadge update

---

## Story

> As a user, I want pipeline run and batch statuses displayed as small colored pills so that I can quickly assess the state of items in lists and tables.

---

## Scope

### In Scope
- New `Badge.tsx` with 7 statuses and 2 sizes
- Processing status pulse animation

### Out of Scope
- Replacing DsoBadge in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Badge.tsx` (new)

```tsx
type BadgeStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "review"
  | "default";

type BadgeSize = "sm" | "md";

interface BadgeProps {
  status: BadgeStatus;
  size?: BadgeSize;
  className?: string;
}

const statusClasses: Record<BadgeStatus, string> = {
  pending: "bg-stone/20 text-stone",
  processing: "bg-indigo-pale text-indigo animate-pulse",
  completed: "bg-success/10 text-success",
  failed: "bg-error/10 text-error",
  cancelled: "bg-stone/20 text-stone",
  review: "bg-warning/10 text-warning",
  default: "bg-linen text-sand",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-sm",
};

export default function Badge({ status, size = "md", className = "" }: BadgeProps) {
  return (
    <span
      className={`
        inline-flex items-center rounded-full font-medium font-body
        ${statusClasses[status]}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
```

### Status Color Map

| Status | Background | Text | Animation |
|--------|-----------|------|-----------|
| `pending` | stone/20 | stone | none |
| `processing` | indigo-pale | indigo | pulse |
| `completed` | success/10 | success | none |
| `failed` | error/10 | error | none |
| `cancelled` | stone/20 | stone | none |
| `review` | warning/10 | warning | none |
| `default` | linen | sand | none |

---

## Acceptance Criteria

- [ ] `status` prop: pending, processing, completed, failed, cancelled, review, default
- [ ] Each status has distinct bg and text color per the color map above
- [ ] Badges are pill-shaped (rounded-full)
- [ ] Processing badge has `animate-pulse`
- [ ] Two sizes: sm (px-2 py-0.5 text-xs), md (px-2.5 py-1 text-sm, default)
- [ ] Label text is capitalized (e.g., "pending" → "Pending")
- [ ] Font: medium weight, font-body

---

## Validation

1. Render all 7 statuses — verify distinct colors
2. Verify processing badge has subtle pulse animation
3. Compare sm vs md sizes side-by-side
