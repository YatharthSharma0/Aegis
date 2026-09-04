import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import type { InvestigationReport } from "../api/report";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import { ErrorState } from "../components/ErrorState";
import { SahyogNoticePanel } from "../components/SahyogNoticePanel";
import { useReport } from "../features/report/useReport";
import { useAuthStore } from "../state/authStore";
import { CopyButton } from "../ui/CopyButton";
import { Mono } from "../ui/Mono";
import { Spinner } from "../ui/Spinner";
import { formatDateTime } from "../ui/formatDate";

export function ReportPage() {
  const { id = "" } = useParams();
  const report = useReport(id);
  const email = useAuthStore((s) => s.email);

  if (report.isLoading) return <Spinner label="Building report" />;
  if (report.isError || !report.data) {
    const notReady =
      report.error instanceof ApiError && report.error.status === 409;
    return (
      <div className="mx-auto max-w-3xl space-y-3">
        {notReady ? (
          <p
            className="rounded-sm border border-dashed border-strong px-6 py-8 text-center text-sm text-muted"
            role="status"
          >
            The trace has not finished yet — the report is available once it
            completes.
          </p>
        ) : (
          <ErrorState
            error={report.error}
            onRetry={() => report.refetch()}
            context="build the report"
          />
        )}
        <Link to={`/trace/${id}`} className="text-sm text-link hover:underline">
          Back to the trace
        </Link>
      </div>
    );
  }

  const r: InvestigationReport = report.data;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-primary">
            Investigation report
          </h1>
          <p className="text-sm text-muted">{r.report_type}</p>
        </div>
        <CopyButton
          value={JSON.stringify(r, null, 2)}
          label="Copy report JSON"
        />
      </header>

      {/* Evidence document — warm paper preview inside the dark app chrome,
          per the forensic-ledger direction (Report and Notice). */}
      <div className="divide-y divide-ink/15 rounded-sm border border-strong bg-paper text-ink shadow-[0_12px_32px_rgb(0_0_0_/_.32)]">
        <Section title="Header">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
            <Detail label="Trace ID">
              <span className="font-mono text-xs">{r.header.trace_id}</span>
            </Detail>
            <Detail label="Case">
              {r.header.case_id ? (
                <Link
                  to={`/cases/${r.header.case_id}`}
                  className="text-link hover:underline"
                >
                  {r.header.case_id}
                </Link>
              ) : (
                "—"
              )}
            </Detail>
            <Detail label="Chain">{r.header.chain}</Detail>
            <Detail label="Reported address">
              <Mono value={r.header.reported_address} className="!text-ink" />
            </Detail>
            <Detail label="Status">
              {r.header.status}
              {r.header.partial_reason ? ` (${r.header.partial_reason})` : ""}
            </Detail>
            <Detail label="Generated">
              {formatDateTime(r.header.generated_at)}
            </Detail>
            <Detail label="Result hash">
              <span className="font-mono text-xs break-all">
                {r.header.result_hash}
              </span>
            </Detail>
          </dl>
        </Section>

        <Section title="Officer summary">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
            {r.officer_summary}
          </p>
        </Section>

        <Section title={`VASP candidates (${r.vasp_candidates.length})`}>
          {r.vasp_candidates.length === 0 ? (
            <p className="text-sm text-ink/60">No VASP attributed.</p>
          ) : (
            <ul className="space-y-3">
              {r.vasp_candidates.map((c) => (
                <li
                  key={c.rank}
                  className={
                    "rounded-sm border p-3 " +
                    (c.verified
                      ? "border-entity-vasp/50"
                      : "border-dashed border-ink/25")
                  }
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-semibold text-ink">
                      #{c.rank} {c.name ?? c.label ?? "Unidentified VASP-like endpoint"}
                    </span>
                    <span className="text-xs uppercase tracking-wide text-ink/60">
                      {c.tier} ·{" "}
                      {c.verified ? "Dataset-confirmed" : "Heuristic — unverified"}
                    </span>
                    <ConfidenceBadge confidence={c.confidence} />
                  </div>
                  {c.deposit_address && (
                    <div className="mt-1 text-sm">
                      <span className="text-ink/60">Deposit: </span>
                      <Mono value={c.deposit_address} className="!text-ink" />
                    </div>
                  )}
                  <div className="mt-1 text-xs text-ink/60">
                    {c.hops_from_seed} hops · {c.reaching_paths} paths ·{" "}
                    {c.evidence.length} evidence records · via {c.source}
                  </div>
                  {c.confidence_formula && (
                    <details className="mt-2 text-xs">
                      <summary className="cursor-pointer text-ink/60 hover:text-ink">
                        Attribution confidence arithmetic (raw{" "}
                        {c.confidence_formula.raw_score} → {c.confidence_formula.score})
                      </summary>
                      <table className="mt-2 w-full">
                        <thead className="text-ink/60">
                          <tr className="text-left">
                            <th className="py-1 pr-3">Term</th>
                            <th className="py-1 pr-3">Value</th>
                            <th className="py-1">Weight</th>
                          </tr>
                        </thead>
                        <tbody className="font-mono">
                          {Object.keys(c.confidence_formula.terms).map((k) => (
                            <tr key={k} className="border-t border-ink/15">
                              <td className="py-1 pr-3 font-sans text-ink/60">
                                {k}
                              </td>
                              <td className="py-1 pr-3">
                                {c.confidence_formula!.terms[k]}
                              </td>
                              <td className="py-1">
                                {c.confidence_formula!.weights[k] ?? "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </details>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title={`Fund flow (${r.fund_flow.length} steps)`}>
          {r.fund_flow.length === 0 ? (
            <p className="text-sm text-ink/60">No transfers recorded.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="text-ink/60">
                  <tr className="border-b border-ink/15 text-left">
                    <th className="py-1 pr-3">#</th>
                    <th className="py-1 pr-3">From → To</th>
                    <th className="py-1 pr-3">Value</th>
                    <th className="py-1 pr-3">Taint</th>
                    <th className="py-1">Tx</th>
                  </tr>
                </thead>
                <tbody>
                  {r.fund_flow.map((s) => (
                    <tr key={s.step} className="border-b border-ink/10">
                      <td className="py-1 pr-3">{s.step}</td>
                      <td className="py-1 pr-3">
                        <div className="flex flex-col gap-0.5">
                          <Mono value={s.from} className="!text-ink" />
                          <Mono value={s.to} className="!text-ink" />
                        </div>
                      </td>
                      <td className="py-1 pr-3 font-mono tabular-nums">
                        {s.value} {s.asset}
                      </td>
                      <td className="py-1 pr-3 font-mono tabular-nums">
                        {Number(s.victim_taint).toFixed(3)}
                      </td>
                      <td className="py-1">
                        <Mono value={s.tx_hash} className="!text-ink" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Section>

        {r.typologies.length > 0 && (
          <Section title="Typologies">
            <ul className="space-y-1 text-sm">
              {r.typologies.map((t, i) => (
                <li key={`${t.name}-${i}`} className="flex justify-between">
                  <span>{t.name}</span>
                  <span className="text-xs text-ink/60">
                    {t.model} · {(Number(t.score) * 100).toFixed(0)}%
                  </span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        <Section title="Data sources">
          {r.data_sources.length === 0 ? (
            <p className="text-sm text-ink/60">No snapshots recorded.</p>
          ) : (
            <ul className="space-y-2 text-xs">
              {r.data_sources.map((s, i) => (
                <li key={i} className="border-b border-ink/10 pb-2">
                  <div className="text-ink">
                    {s.provider} · {s.endpoint}
                  </div>
                  <div className="text-ink/60">
                    captured {formatDateTime(s.captured_at)} · tip #
                    {s.tip_block.height} · {s.record_count} records
                  </div>
                  <div className="font-mono text-ink/60 break-all">
                    checksum {s.response_checksum}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section title="Certification">
          <p className="text-sm leading-relaxed text-ink">
            {r.certification.statement}
          </p>
          <dl className="mt-2 text-xs text-ink/60">
            <div>Method: {r.certification.method}</div>
            <div>
              Reproducibility anchor:{" "}
              <span className="font-mono break-all">
                {r.certification.reproducibility_anchor}
              </span>
            </div>
          </dl>
          {r.caveats.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-ink/60">
              {r.caveats.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <SahyogNoticePanel
        traceId={id}
        candidateCount={r.vasp_candidates.length}
        defaultOfficer={r.header.generated_by ?? email}
        defaultCaseRef={r.header.case_id}
      />
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="p-4 sm:p-5">
      <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink">
        {title}
      </h2>
      {children}
    </section>
  );
}

function Detail({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <dt className="text-xs text-ink/60">{label}</dt>
      <dd className="mt-0.5 text-ink">{children}</dd>
    </div>
  );
}
