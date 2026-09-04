import type { ReactNode } from "react";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-xs text-mute" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && !error && <p className="text-xs text-mute">{hint}</p>}
      {error && (
        <p className="text-xs text-risk-high" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
