import { forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary: "bg-indigo text-snow hover:bg-indigo-light active:scale-[0.98]",
  secondary: "bg-snow text-charcoal border border-linen hover:bg-cream active:scale-[0.98]",
  danger: "bg-error text-snow hover:opacity-90 active:scale-[0.98]",
  ghost: "bg-transparent text-charcoal hover:bg-cream active:scale-[0.98]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", className = "", disabled, children, ...props }, ref) => {
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
  },
);

Button.displayName = "Button";
export default Button;
