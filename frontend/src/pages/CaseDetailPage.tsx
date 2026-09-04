import { useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import type { CaseStatus } from "../api/types";
import { CaseStatusBadge } from "../components/CaseStatusBadge";
import {
  useAddComplaint,
  useCase,
  useUpdateCase,
} from "../features/cases/useCases";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Field } from "../ui/Field";
import { textInputClass } from "../ui/inputClass";
import { formatDateTime } from "../ui/formatDate";
import { Mono } from "../ui/Mono";
import { Spinner } from "../ui/Spinner";

const STATUSES: CaseStatus[] = ["open", "in_progress", "closed"];

export function CaseDetailPage() {
  const { id = "" } = useParams();
  const { data, isLoading, isError, error } = useCase(id);
  const update = useUpdateCase(id);

  if (isLoading) return <Spinner label="Loading case" />;
  if (isError || !data) {
    return (
      <div className="mx-auto max-w-3xl space-y-3">
        <p className="text-sm text-risk-high" role="alert">
          {error instanceof ApiError && error.status === 404
            ? "That case does not exist."
            : "Could not load the case."}
        </p>
        <Link to="/cases" className="text-sm text-indigo-300 hover:underline">
          Back to cases
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <Link to="/cases" className="text-xs text-mute hover:text-slate-300">
          ← Cases
        </Link>
        <div className="mt-1 flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">{data.title}</h1>
            <p className="text-sm text-mute">
              {data.ref_no}
              {data.typology_hint ? ` · ${data.typology_hint}` : ""}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <CaseStatusBadge status={data.status} />
            <select
              aria-label="Change status"
              value={data.status}
              disabled={update.isPending}
              onChange={(e) =>
                update.mutate({ status: e.target.value as CaseStatus })
              }
              className={textInputClass("w-auto py-1 text-xs")}
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="mt-1 text-xs text-mute">
          Opened {formatDateTime(data.created_at)}
          {data.created_by ? ` by ${data.created_by}` : ""}
        </p>
        {update.isError && (
          <p className="mt-1 text-xs text-risk-high" role="alert">
            Status update failed.
          </p>
        )}
      </div>

      {data.notes && (
        <Card title="Notes">
          <p className="whitespace-pre-wrap text-sm text-slate-300">
            {data.notes}
          </p>
        </Card>
      )}

      <Card
        title="Complaints"
        actions={
          <span className="text-xs text-mute">{data.complaints.length}</span>
        }
      >
        {data.complaints.length === 0 ? (
          <EmptyState message="No complaint text attached yet. Add the victim's report below." />
        ) : (
          <ul className="mb-4 divide-y divide-navy-700">
            {data.complaints.map((c) => (
              <li key={c.id} className="py-2.5">
                <div className="flex items-center gap-2 text-xs text-mute">
                  <span className="uppercase tracking-wide">{c.source}</span>
                  {c.is_demo && (
                    <span className="rounded-sm border border-navy-600 px-1">
                      demo
                    </span>
                  )}
                  <span>{formatDateTime(c.received_at)}</span>
                </div>
                <p className="mt-1 text-sm text-slate-300">{c.text_preview}</p>
              </li>
            ))}
          </ul>
        )}
        <AddComplaintForm caseId={id} />
      </Card>

      <Card title="Trace runs">
        {data.trace_runs.length === 0 ? (
          <EmptyState
            message="No traces run for this case yet."
            action={
              <Link
                to={`/trace/new?case=${encodeURIComponent(id)}`}
                className="text-sm font-medium text-indigo-300 hover:underline"
              >
                Start a trace
              </Link>
            }
          />
        ) : (
          <ul className="divide-y divide-navy-700">
            {data.trace_runs.map((t) => (
              <li key={t.trace_id}>
                <Link
                  to={`/trace/${t.trace_id}`}
                  className="flex items-center justify-between gap-3 py-2.5 hover:bg-white/5"
                >
                  <Mono value={t.start_address} />
                  <span className="flex items-center gap-3 text-xs text-mute">
                    <span className="uppercase tracking-wide">{t.status}</span>
                    <span>{formatDateTime(t.created_at)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function AddComplaintForm({ caseId }: { caseId: string }) {
  const add = useAddComplaint(caseId);
  const [text, setText] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    add.mutate(
      { text: text.trim(), source: "manual", is_demo: false },
      { onSuccess: () => setText("") },
    );
  };

  return (
    <form onSubmit={submit} className="space-y-2">
      <Field label="Add complaint text" htmlFor="complaint">
        <textarea
          id="complaint"
          rows={3}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Paste the victim's NCRP / 1930 report…"
          className={textInputClass()}
        />
      </Field>
      <div className="flex items-center gap-2">
        <Button type="submit" loading={add.isPending} disabled={!text.trim()}>
          Attach
        </Button>
        {add.isError && (
          <span className="text-xs text-risk-high" role="alert">
            Could not attach the complaint.
          </span>
        )}
      </div>
    </form>
  );
}
