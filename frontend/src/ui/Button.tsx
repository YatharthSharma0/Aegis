import type { ButtonHTMLAttributes } from "react";

import { cn } from "./cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const styles: Record<Variant, string> = {
  primary: "bg-brand text-ink hover:bg-brand-hover",
  secondary: "border border-strong text-secondary hover:bg-hover hover:text-primary",
  ghost: "text-secondary hover:bg-hover hover:text-primary",
  danger: "bg-risk-high text-ink hover:brightness-110",
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  className,
  children,
  ...rest
}: Props) {
  return (
    <button
      className={cn(
        "inline-flex h-10 items-center justify-center gap-2 rounded-sm px-4 text-sm font-medium",
        "transition-colors duration-fast disabled:cursor-not-allowed disabled:opacity-[.42]",
        styles[variant],
        className,
      )}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && (
        <span
          className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden
        />
      )}
      {children}
    </button>
  );
}
