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
            hover:border-indigo/50
            focus-visible:outline-none focus-visible:border-indigo focus-visible:ring-2 focus-visible:ring-indigo/20
            ${error ? "border-error" : "border-linen"}
            ${className}
          `}
          {...props}
        />
        {error && <p className="text-error text-xs mt-1 font-body">{error}</p>}
      </div>
    );
  },
);

Input.displayName = "Input";
export default Input;
