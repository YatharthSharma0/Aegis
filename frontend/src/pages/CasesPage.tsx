import { useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import type { CaseStatus } from "../api/types";
import { CaseStatusBadge } from "../components/CaseStatusBadge";
import { ErrorState } from "../components/ErrorState";
import { useCases, useCreateCase } from "../features/cases/useCases";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { Field } from "../ui/Field";
import { textInputClass } from "../ui/inputClass";
import { formatDateTime } from "../ui/formatDate";
import { Spinner } from "../ui/Spinner";

const STATUS_FILTERS: Array<{ value: CaseStatus | "all"; label: string }> = [
  { value: "all", label: "All" },
  { value: "open", label: "Open" },
  { value: "in_progress", label: "In progress" },
  { value: "closed", label: "Closed" },
];

export function CasesPage() {
  const [filter, setFilter] = useState<CaseStatus | "all">("all");
  const cases = useCases(filter === "all" ? {} : { status: filter });

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <header className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-primary">Cases</h1>
          <p className="text-sm text-muted">
            Investigations grouped by FIR / NCRP reference.
          </p>
        </div>
        <div className="flex gap-1">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              aria-pressed={filter === f.value}
              className={
                "rounded-sm border px-2.5 py-1 text-xs transition-colors duration-fast " +
                (filter === f.value
                  ? "border-brand text-brand"
                  : "border-subtle text-muted hover:text-secondary")
              }
            >
              {f.label}
            </button>
          ))}
        </div>
      </header>

      <CreateCaseForm />

      <Card title="Case list">
        {cases.isLoading && <Spinner label="Loading cases" />}
        {cases.isError && (
          <ErrorState
            error={cases.error}
            onRetry={() => cases.refetch()}
            context="load cases"
          />
        )}
        {cases.data && cases.data.length === 0 && (
          <EmptyState message="No cases match this filter. Create one above to begin." />
        )}
        {cases.data && cases.data.length > 0 && (
          <ul className="divide-y divide-subtle">
            {cases.data.map((c) => (
              <li key={c.id}>
                <Link
                  to={`/cases/${c.id}`}
                  className="flex items-center justify-between gap-4 py-3 transition-colors duration-fast hover:bg-hover"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-primary">
                      {c.title}
                    </div>
                    <div className="text-xs text-muted">
                      {c.ref_no} · updated {formatDateTime(c.updated_at)}
                    </div>
                  </div>
                  <CaseStatusBadge status={c.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function CreateCaseForm() {
  const create = useCreateCase();
  const [refNo, setRefNo] = useState("");
  const [title, setTitle] = useState("");
  const [typology, setTypology] = useState("");
  const [open, setOpen] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate(
      {
        ref_no: refNo.trim(),
        title: title.trim(),
        typology_hint: typology.trim() || null,
      },
      {
        onSuccess: () => {
          setRefNo("");
          setTitle("");
          setTypology("");
          setOpen(false);
        },
      },
    );
  };

  if (!open) {
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        New case
      </Button>
    );
  }

  return (
    <Card title="New case">
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <Field label="Reference no." htmlFor="ref_no">
          <input
            id="ref_no"
            required
            value={refNo}
            onChange={(e) => setRefNo(e.target.value)}
            placeholder="FIR 0123/2026"
            className={textInputClass()}
          />
        </Field>
        <Field label="Title" htmlFor="title">
          <input
            id="title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="USDT drain — victim complaint"
            className={textInputClass()}
          />
        </Field>
        <Field label="Typology hint (optional)" htmlFor="typology">
          <input
            id="typology"
            value={typology}
            onChange={(e) => setTypology(e.target.value)}
            placeholder="layering / peel chain"
            className={textInputClass()}
          />
        </Field>
        <div className="flex items-end gap-2">
          <Button type="submit" loading={create.isPending}>
            Create
          </Button>
          <Button type="button" variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
        {create.isError && (
          <p className="text-sm text-risk-high sm:col-span-2" role="alert">
            {create.error instanceof ApiError
              ? create.error.message
              : "Could not create the case."}
          </p>
        )}
      </form>
    </Card>
  );
}
