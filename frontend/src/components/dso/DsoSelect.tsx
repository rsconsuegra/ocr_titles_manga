import { type SelectHTMLAttributes, forwardRef } from "react";

interface DsoSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

export const DsoSelect = forwardRef<HTMLSelectElement, DsoSelectProps>(
  ({ label, className = "", id, children, ...props }, ref) => {
    return (
      <div className="flex flex-col gap-1">
        {label && (
          <label htmlFor={id} className="tech-label">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={id}
          className={[
            "w-full rounded-lg border border-highlight/20 bg-inset px-3 py-2 text-sm text-bright",
            "focus:border-teal/40 focus:outline-none focus:ring-1 focus:ring-teal/30",
            "transition-colors duration-150",
            "appearance-none",
            className,
          ].join(" ")}
          {...props}
        >
          {children}
        </select>
      </div>
    );
  },
);

DsoSelect.displayName = "DsoSelect";
