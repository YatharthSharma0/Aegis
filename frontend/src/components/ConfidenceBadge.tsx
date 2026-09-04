import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";

import {
  clampConfidence,
  confidenceBand,
  type ConfidenceBand,
} from "../features/trace/confidence";
import { cn } from "../ui/cn";

const META: Record<
  ConfidenceBand,
  { label: string; icon: typeof ShieldCheck; className: string }
> = {
  high: {
    label: "High confidence",
    icon: ShieldCheck,
    className: "text-confirmed border-confirmed/40 bg-confirmed/10",
  },
  medium: {
    label: "Medium confidence",
    icon: ShieldAlert,
    className: "text-risk-med border-risk-med/40 bg-risk-med/10",
  },
  low: {
    label: "Low confidence",
    icon: ShieldQuestion,
    className: "text-risk-high border-risk-high/40 bg-risk-high/10",
  },
};

/** Confidence is shown as icon + word + percent — never colour alone. */
export function ConfidenceBadge({
  confidence,
  className,
}: {
  confidence: string | number;
  className?: string;
}) {
  const safe = clampConfidence(confidence);
  const meta = META[confidenceBand(safe)];
  const Icon = meta.icon;
  const pct = (safe * 100).toFixed(0);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium",
        meta.className,
        className,
      )}
      title={`${meta.label} — ${pct}%`}
    >
      <Icon size={13} aria-hidden />
      {meta.label} · {pct}%
    </span>
  );
}
