import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { cn } from "./cn";

export function CopyButton({
  value,
  label = "Copy",
  className,
}: {
  value: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — no-op */
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border border-subtle px-2.5 py-1 text-xs text-secondary transition-colors duration-fast hover:bg-hover hover:text-primary",
        className,
      )}
    >
      {copied ? (
        <Check size={13} className="text-success" aria-hidden />
      ) : (
        <Copy size={13} aria-hidden />
      )}
      {copied ? "Copied" : label}
    </button>
  );
}
