import { BadgeCheck, HelpCircle } from "lucide-react";

import type { VaspCandidateOut } from "../api/types";
import { Card } from "../ui/Card";
import { cn } from "../ui/cn";
import { Mono } from "../ui/Mono";
import { ConfidenceBadge } from "./ConfidenceBadge";

/**
 * The attributed exchange / VASP for a trace — the headline answer.
 * Confirmed attribution gets a solid entity-teal border; heuristic
 * (unverified) attribution gets a dashed border — the same "known vs
 * inferred" grammar as the graph. Neither is coloured as risk.
 */
export function VaspMatchCard({
  candidate,
  headline = false,
}: {
  candidate: VaspCandidateOut;
  headline?: boolean;
}) {
  const name = candidate.name ?? candidate.label ?? "Unidentified VASP-like endpoint";
  const terms = candidate.confidence_terms ?? {};

  return (
    <Card
      title={headline ? "Attributed VASP" : `Candidate #${candidate.rank}`}
      actions={<ConfidenceBadge confidence={candidate.confidence} />}
      className={cn(
        candidate.verified
          ? "border-entity-vasp/60"
          : "border-dashed border-strong",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        {candidate.verified ? (
          <BadgeCheck size={18} className="text-entity-vasp" aria-hidden />
        ) : (
          <HelpCircle size={18} className="text-muted" aria-hidden />
        )}
        <span className="text-base font-semibold text-primary">{name}</span>
        <span className="rounded-sm border border-subtle px-1.5 py-0.5 text-[11px] uppercase tracking-wide text-muted">
          {candidate.tier}
        </span>
        <span className="text-xs text-muted">
          {candidate.verified ? "Dataset-confirmed" : "Heuristic — unverified"} · via{" "}
          {candidate.source}
        </span>
      </div>

      {candidate.deposit_address && (
        <div className="mt-2 text-sm">
          <span className="text-muted">Deposit address: </span>
          <Mono value={candidate.deposit_address} />
        </div>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-muted">Hops from seed</dt>
          <dd className="font-mono tabular-nums">{candidate.hops_from_seed}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Reaching paths</dt>
          <dd className="font-mono tabular-nums">{candidate.reaching_paths}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted">Evidence records</dt>
          <dd className="font-mono tabular-nums">{candidate.evidence.length}</dd>
        </div>
      </dl>

      {candidate.signals.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {candidate.signals.map((s) => (
            <span
              key={s}
              className="rounded-sm border border-subtle px-1.5 py-0.5 text-xs text-secondary"
            >
              {s}
            </span>
          ))}
        </div>
      )}

      {Object.keys(terms).length > 0 && (
        <details className="mt-3 text-sm">
          <summary className="cursor-pointer text-xs text-muted hover:text-secondary">
            Attribution confidence breakdown
          </summary>
          <table className="mt-2 w-full text-xs">
            <tbody>
              {Object.entries(terms).map(([k, v]) => (
                <tr key={k} className="border-t border-subtle">
                  <td className="py-1 pr-3 text-muted">{k}</td>
                  <td className="py-1 text-right font-mono tabular-nums">
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
