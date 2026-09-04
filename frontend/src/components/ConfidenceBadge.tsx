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
    label: "High attribution confidence",
    icon: ShieldCheck,
    className: "text-entity-vasp border-entity-vasp/40 bg-entity-vasp/10",
  },
  medium: {
    label: "Medium attribution confidence",
    icon: ShieldAlert,
    className: "text-warning border-warning/40 bg-warning/10",
  },
  low: {
    label: "Low attribution confidence",
    icon: ShieldQuestion,
    className: "text-unknown border-strong bg-hover",
  },
};

/**
 * Attribution confidence — how confident the service/entity match is. Kept
 * visually distinct from fraud risk (never rendered in `risk-*` colour) and
 * shown as icon + word + percent, never colour alone.
 */
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
