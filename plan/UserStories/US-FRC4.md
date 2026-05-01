# US-FRC4: Use New Input and Select Components

**Sub-phase**: FR-C — Component Library
**Depends on**: US-FRA2 (color tokens)
**Blocks**: US-FRC7 (DSO removal replaces DsoInput/DsoSelect)

---

## Story

> As a user, I want form inputs and dropdowns to have consistent warm styling with clear focus states so that filling in forms feels polished and predictable.

---

## Scope

### In Scope
- New `Input.tsx` with label, error state, focus ring
- New `Select.tsx` with options array, custom chevron, same base styling

### Out of Scope
- Replacing DsoInput/DsoSelect in pages (US-FRC7)

---

## Implementation Details

### 1. `frontend/src/components/ui/Input.tsx` (new)

```tsx
import { forwardRef } from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={inputId} className="label-text block mb-1.5">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={`
            w-full bg-snow border rounded-md px-3 py-2 text-charcoal font-body text-sm
            placeholder:text-sand
            focus:outline-none focus:border-indigo focus:ring-2 focus:ring-indigo/20
            ${error ? "border-error" : "border-linen"}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-error text-xs mt-1 font-body">{error}</p>}
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
```

### 2. `frontend/src/components/ui/Select.tsx` (new)

```tsx
import { forwardRef } from "react";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  placeholder?: string;
  error?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, options, placeholder, error, className = "", id, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label htmlFor={selectId} className="label-text block mb-1.5">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={`
            w-full bg-snow border rounded-md px-3 py-2 text-charcoal font-body text-sm
            appearance-none
            bg-[url('data:image/svg+xml;charset=utf-8,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2216%22%20height%3D%2216%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%239B9288%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E')]
            bg-no-repeat bg-[right_0.5rem_center] bg-[length:1.25rem]
            focus:outline-none focus:border-indigo focus:ring-2 focus:ring-indigo/20
            ${error ? "border-error" : "border-linen"}
            ${className}
          `}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="text-error text-xs mt-1 font-body">{error}</p>}
      </div>
    );
  }
);

Select.displayName = "Select";
export default Select;
```

---

## Acceptance Criteria

- [ ] Input: bg-snow, border-linen, rounded-md, px-3 py-2, text-charcoal, font-body
- [ ] Input focus: border-indigo, ring-2 ring-indigo/20
- [ ] Input error state: border-error + red helper text below
- [ ] Input `label` prop renders above in label-text style
- [ ] Input auto-generates `id` from label for label association
- [ ] Input extends native HTMLInputElement attributes
- [ ] Select: same base styling as Input
- [ ] Select: appearance-none with custom chevron SVG
- [ ] Select accepts `options: {value, label}[]` array
- [ ] Select accepts optional `placeholder` prop
- [ ] Both use `forwardRef` for ref forwarding

---

## Validation

1. Render Input with label — verify label text above, input focusable
2. Set `error` prop — verify red border + error text
3. Render Select with 3 options — verify dropdown opens, chevron visible
4. Tab through inputs — verify focus ring on each
