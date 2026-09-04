import { BadgeCheck, HelpCircle } from "lucide-react";

import type { VaspCandidateOut } from "../api/types";
import { Card } from "../ui/Card";
import { Mono } from "../ui/Mono";
import { ConfidenceBadge } from "./ConfidenceBadge";

/** The attributed exchange / VASP for a trace — the headline answer. */
export function VaspMatchCard({
  candidate,
  headline = false,
}: {
  candidate: VaspCandidateOut;
  headline?: boolean;
}) {
  const name = candidate.name ?? candidate.label ?? "Unattributed";
  const terms = candidate.confidence_terms ?? {};

  return (
    <Card
      title={headline ? "Attributed VASP" : `Candidate #${candidate.rank}`}
      actions={<ConfidenceBadge confidence={candidate.confidence} />}
    >
      <div className="flex items-center gap-2">
        {candidate.verified ? (
          <BadgeCheck size={18} className="text-confirmed" aria-hidden />
        ) : (
          <HelpCircle size={18} className="text-mute" aria-hidden />
        )}
        <span className="text-base font-semibold text-slate-100">{name}</span>
        <span className="rounded-sm border border-navy-600 px-1.5 py-0.5 text-[11px] uppercase tracking-wide text-mute">
          {candidate.tier}
        </span>
        <span className="text-xs text-mute">
          {candidate.verified ? "dataset-confirmed" : "heuristic"} · via{" "}
          {candidate.source}
        </span>
      </div>

      {candidate.deposit_address && (
        <div className="mt-2 text-sm">
          <span className="text-mute">Deposit address: </span>
          <Mono value={candidate.deposit_address} />
        </div>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-mute">Hops from seed</dt>
          <dd>{candidate.hops_from_seed}</dd>
        </div>
        <div>
          <dt className="text-xs text-mute">Reaching paths</dt>
          <dd>{candidate.reaching_paths}</dd>
        </div>
        <div>
          <dt className="text-xs text-mute">Evidence records</dt>
          <dd>{candidate.evidence.length}</dd>
        </div>
      </dl>

      {candidate.signals.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {candidate.signals.map((s) => (
            <span
              key={s}
              className="rounded-sm border border-navy-600 px-1.5 py-0.5 text-xs text-slate-300"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {Object.keys(terms).length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-xs text-mute hover:text-slate-300">
            Confidence breakdown
          </summary>
          <table className="mt-2 w-full text-xs">
            <tbody>
              {Object.entries(terms).map(([k, v]) => (
                <tr key={k} className="border-t border-navy-700">
                  <td className="py-1 pr-3 text-mute">{k}</td>
                  <td className="py-1 text-right font-mono">
                    {Number(v).toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </Card>
  );
}
