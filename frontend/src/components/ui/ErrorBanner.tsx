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
