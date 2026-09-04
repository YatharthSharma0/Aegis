import { ShieldCheck, ShieldX } from "lucide-react";
import { useState } from "react";

import type { AuditVerificationOut } from "../api/types";
import { ErrorState } from "../components/ErrorState";
import { useAudit } from "../features/admin/useAudit";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Mono } from "../ui/Mono";
import { Spinner } from "../ui/Spinner";
import { formatDateTime } from "../ui/formatDate";
import { textInputClass } from "../ui/inputClass";

export function AdminAuditPage() {
  const [action, setAction] = useState("");
  const audit = useAudit(action ? { action, limit: 200 } : { limit: 200 });

  return (
    <div className="mx-auto max-w-5xl space-y-4">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Audit log</h1>
          <p className="text-sm text-mute">
            Hash-chained, append-only record of every privileged action.
          </p>
        </div>
        <input
          aria-label="Filter by action"
          value={action}
          onChange={(e) => setAction(e.target.value)}
          placeholder="filter action e.g. trace.start"
          className={textInputClass("w-56 text-sm")}
        />
      </header>

      {audit.data && <VerificationBanner v={audit.data.verification} />}

      <Card>
        {audit.isLoading && <Spinner label="Loading audit log" />}
        {audit.isError && (
          <ErrorState error={audit.error} onRetry={() => audit.refetch()} />
        )}
        {audit.data && audit.data.entries.length === 0 && (
          <EmptyState message="No audit entries match this filter." />
        )}
        {audit.data && audit.data.entries.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-mute">
                <tr className="border-b border-navy-700 text-left">
                  <th className="py-1.5 pr-3">Seq</th>
                  <th className="py-1.5 pr-3">Time</th>
                  <th className="py-1.5 pr-3">Actor</th>
                  <th className="py-1.5 pr-3">Action</th>
                  <th className="py-1.5 pr-3">Target</th>
                  <th className="py-1.5">Row hash</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.entries.map((e) => (
                  <tr key={e.seq} className="border-b border-navy-800 align-top">
                    <td className="py-1.5 pr-3 font-mono">{e.seq}</td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {formatDateTime(e.ts)}
                    </td>
                    <td className="py-1.5 pr-3">
                      {e.actor_id ?? "—"}
                      {e.actor_role ? (
                        <span className="text-mute"> · {e.actor_role}</span>
                      ) : null}
                    </td>
                    <td className="py-1.5 pr-3 font-mono">{e.action}</td>
                    <td className="py-1.5 pr-3">
                      {e.trace_id && <Mono value={e.trace_id} />}
                      {e.case_id && <span> {e.case_id}</span>}
                      {e.address && <Mono value={e.address} />}
                    </td>
                    <td className="py-1.5">
                      <Mono value={e.row_hash} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

function VerificationBanner({ v }: { v: AuditVerificationOut }) {
  if (v.ok) {
    return (
      <div className="flex items-center gap-2 rounded-sm border border-risk-low/40 px-3 py-2 text-sm text-risk-low">
        <ShieldCheck size={16} aria-hidden />
        Chain intact — {v.checked} entries verified.
      </div>
    );
  }
  return (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-sm border border-risk-high/40 px-3 py-2 text-sm text-risk-high"
    >
      <ShieldX size={16} aria-hidden />
      Chain broken at seq {v.broken_at_seq ?? "?"}
      {v.reason ? ` — ${v.reason}` : ""}
    </div>
  );
}
