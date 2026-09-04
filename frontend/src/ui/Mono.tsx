import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { cn } from "./cn";

/** A blockchain address / hash: monospace, middle-truncated, copy-on-click,
 * full value on hover (Style Guide). */
export function Mono({
  value,
  truncate = true,
  className,
}: {
  value: string;
  truncate?: boolean;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);
  const shown =
    truncate && value.length > 16
      ? `${value.slice(0, 8)}…${value.slice(-6)}`
      : value;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    } catch {
      /* clipboard unavailable — no-op */
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      title={value}
      className={cn(
        "group inline-flex items-center gap-1.5 font-mono text-[13px] text-slate-300 hover:text-white",
        className,
      )}
    >
      <span>{shown}</span>
      {copied ? (
        <Check size={13} className="text-risk-low" aria-label="copied" />
      ) : (
        <Copy
          size={13}
          className="opacity-0 transition-opacity group-hover:opacity-60"
          aria-hidden
        />
      )}
    </button>
  );
}
