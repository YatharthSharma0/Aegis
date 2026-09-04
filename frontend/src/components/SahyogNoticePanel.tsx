import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import type { SahyogNoticeParams } from "../api/report";
import { useSahyogNotice } from "../features/report/useReport";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { CopyButton } from "../ui/CopyButton";
import { Field } from "../ui/Field";
import { textInputClass } from "../ui/inputClass";

/** Generate an editable SAHYOG preservation-request draft from the trace.
 * The backend has no store for edits — the officer copies the final text out. */
export function SahyogNoticePanel({
  traceId,
  candidateCount,
  defaultOfficer,
  defaultCaseRef,
}: {
  traceId: string;
  candidateCount: number;
  defaultOfficer?: string | null;
  defaultCaseRef?: string | null;
}) {
  const gen = useSahyogNotice(traceId);
  const [rank, setRank] = useState(1);
  const [officer, setOfficer] = useState(defaultOfficer ?? "");
  const [caseRef, setCaseRef] = useState(defaultCaseRef ?? "");
  const [legalBasis, setLegalBasis] = useState("");
  const [draft, setDraft] = useState("");
  const [subject, setSubject] = useState("");

  useEffect(() => {
    if (gen.data) {
      setDraft(gen.data.notice_draft.body_markdown);
      setSubject(gen.data.notice_draft.subject);
    }
  }, [gen.data]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const params: SahyogNoticeParams = {
      vasp_rank: rank,
      requesting_officer: officer.trim() || null,
      case_ref: caseRef.trim() || null,
      legal_basis: legalBasis.trim() || null,
    };
    gen.mutate(params);
  };

  return (
    <Card title="SAHYOG notice draft">
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="VASP candidate rank" htmlFor="vasp_rank">
          <select
            id="vasp_rank"
            value={rank}
            onChange={(e) => setRank(Number(e.target.value))}
            className={textInputClass()}
          >
            {Array.from({ length: Math.max(1, candidateCount) }, (_, i) => i + 1).map(
              (r) => (
                <option key={r} value={r}>
                  #{r}
                </option>
              ),
            )}
          </select>
        </Field>
        <Field label="Requesting officer" htmlFor="officer">
          <input
            id="officer"
            value={officer}
            onChange={(e) => setOfficer(e.target.value)}
            className={textInputClass()}
          />
        </Field>
        <Field label="Case reference" htmlFor="case_ref">
          <input
            id="case_ref"
            value={caseRef}
            onChange={(e) => setCaseRef(e.target.value)}
            className={textInputClass()}
          />
        </Field>
        <Field label="Legal basis (optional)" htmlFor="legal_basis">
          <input
            id="legal_basis"
            value={legalBasis}
            onChange={(e) => setLegalBasis(e.target.value)}
            placeholder="IT Act s.79(3)(b) r/w BNSS"
            className={textInputClass()}
          />
        </Field>
        <div className="sm:col-span-2">
          <Button type="submit" loading={gen.isPending}>
            {gen.data ? "Regenerate draft" : "Generate draft"}
          </Button>
          {gen.isError && (
            <span className="ml-3 text-sm text-risk-high" role="alert">
              {gen.error instanceof ApiError
                ? gen.error.message
                : "Could not generate the notice."}
            </span>
          )}
        </div>
      </form>

      {gen.data && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between gap-3">
            <div className="text-xs text-muted">
              To: {gen.data.notice_draft.to} · Basis:{" "}
              {gen.data.notice_draft.legal_basis}
            </div>
            <CopyButton
              value={`Subject: ${subject}\n\n${draft}`}
              label="Copy notice"
            />
          </div>
          <input
            aria-label="Notice subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className={textInputClass("text-sm")}
          />
          <textarea
            aria-label="Notice body"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={18}
            className={textInputClass("font-mono text-xs leading-relaxed")}
          />
          <p className="text-xs text-muted">
            Edits stay in this browser. Copy the final text into your official
            template before sending.
          </p>
        </div>
      )}
    </Card>
  );
}
