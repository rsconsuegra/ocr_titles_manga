import { forwardRef,type InputHTMLAttributes } from "react";

interface DsoInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export const DsoInput = forwardRef<HTMLInputElement, DsoInputProps>(
  ({ label, className = "", id, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={id} className="tech-label">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={[
            "w-full rounded-lg border border-highlight/20 bg-inset px-3 py-2 text-sm text-bright",
            "placeholder:text-muted/60",
            "focus:border-teal/40 focus:outline-none focus:ring-1 focus:ring-teal/30",
            "transition-colors duration-150",
            className,
          ].join(" ")}
          {...props}
        />
      </div>
    );
  },
);

DsoInput.displayName = "DsoInput";
