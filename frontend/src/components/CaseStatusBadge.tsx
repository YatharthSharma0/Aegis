import { CheckCircle2, Circle, CircleDot, type LucideIcon } from "lucide-react";

import type { CaseStatus } from "../api/types";
import { cn } from "../ui/cn";

const MAP: Record<
  CaseStatus,
  { label: string; icon: LucideIcon; className: string }
> = {
  open: {
    label: "Open",
    icon: Circle,
    className: "text-info border-info/40 bg-info/10",
  },
  in_progress: {
    label: "In progress",
    icon: CircleDot,
    className: "text-warning border-warning/40 bg-warning/10",
  },
  closed: {
    label: "Closed",
    icon: CheckCircle2,
    className: "text-success border-success/40 bg-success/10",
  },
};

/** Status is never colour-only — always icon + word. */
export function CaseStatusBadge({ status }: { status: CaseStatus | string }) {
  const meta = MAP[status as CaseStatus] ?? {
    label: status,
    icon: Circle,
    className: "text-unknown border-strong bg-hover",
  };
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium",
        meta.className,
      )}
    >
      <Icon size={12} aria-hidden />
      {meta.label}
    </span>
  );
}
