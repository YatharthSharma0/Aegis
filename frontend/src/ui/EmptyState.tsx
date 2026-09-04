import type { ReactNode } from "react";

/** One line + a single next action — never a blank panel (Style Guide). */
export function EmptyState({
  message,
  action,
}: {
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded border border-dashed border-navy-700 px-6 py-10 text-center">
      <p className="text-sm text-mute">{message}</p>
      {action}
    </div>
  );
}
