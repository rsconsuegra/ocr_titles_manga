# US-FRC1: Use New Button Component

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens)
**Blocks**: US-FRC7 (DSO removal replaces DsoButton with Button), all page stories

---

## Story

> As a user, I want buttons to have a clean, warm appearance with clear visual hierarchy (primary, secondary, danger, ghost) so that I can quickly identify the most important action on any page.

---

## Scope

### In Scope
- New `Button.tsx` component with 4 variants and 3 sizes
- Full native HTML button attribute support
- Hover, focus, active, disabled states

### Out of Scope
- Replacing DsoButton in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Button.tsx` (new)

```tsx
import { forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-indigo text-snow hover:bg-indigo-light active:scale-[0.98]",
  secondary:
    "bg-snow text-charcoal border border-linen hover:bg-cream active:scale-[0.98]",
  danger:
    "bg-error text-snow hover:opacity-90 active:scale-[0.98]",
  ghost:
    "bg-transparent text-charcoal hover:bg-cream active:scale-[0.98]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "md", size = "md", className = "", disabled, children, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={`
          inline-flex items-center justify-center rounded-lg
          font-medium font-body transition-colors
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo/20 focus-visible:ring-offset-2
          disabled:opacity-40 disabled:cursor-not-allowed
          ${variantClasses[variant]}
          ${sizeClasses[size]}
          ${className}
        `}
        disabled={disabled}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
```

### Variant Reference

| Variant | Background | Text | Border | Hover |
|---------|-----------|------|--------|-------|
| `primary` | indigo (#2E4A7A) | snow | none | bg-indigo-light |
| `secondary` | snow | charcoal | linen | bg-cream |
| `danger` | error (#B84040) | snow | none | opacity-90 |
| `ghost` | transparent | charcoal | none | bg-cream |

### Size Reference

| Size | Padding | Font |
|------|---------|------|
| `sm` | px-3 py-1.5 | text-sm |
| `md` | px-4 py-2 | text-sm |
| `lg` | px-6 py-3 | text-base |

---

## Acceptance Criteria

- [ ] `variant` prop: "primary" | "secondary" | "danger" | "ghost" (default: "primary")
- [ ] `size` prop: "sm" | "md" | "lg" (default: "md")
- [ ] All buttons: rounded-lg, font-medium font-body
- [ ] Primary: bg-indigo text-snow hover:bg-indigo-light
- [ ] Secondary: bg-snow text-charcoal border-linen hover:bg-cream
- [ ] Danger: bg-error text-snow
- [ ] Ghost: bg-transparent text-charcoal hover:bg-cream
- [ ] All buttons: active:scale-[0.98]
- [ ] Disabled: opacity-40 cursor-not-allowed
- [ ] Focus-visible: ring-2 ring-indigo/20 ring-offset-2
- [ ] Extends native HTMLButtonElement attributes (onClick, type, form, etc.)
- [ ] Uses `forwardRef` for ref forwarding

---

## Validation

1. Render all 4 variants side-by-side — verify visual distinction
2. Hover each variant — verify hover state changes
3. Tab to each button — verify focus ring appears
4. Set `disabled` — verify opacity reduced and no click
