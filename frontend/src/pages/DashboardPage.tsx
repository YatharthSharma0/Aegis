import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { CaseStatusBadge } from "../components/CaseStatusBadge";
import { useCases } from "../features/cases/useCases";
import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";
import { formatDateTime } from "../ui/formatDate";
import { Spinner } from "../ui/Spinner";

export function DashboardPage() {
  const cases = useCases({ limit: 8 });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-mute">Recent cases and quick actions.</p>
      </header>

      <div className="flex gap-2">
        <Link
          to="/trace/new"
          className="rounded-sm bg-indigo-500 px-4 py-2 text-sm font-medium text-white hover:brightness-110"
        >
          New trace
        </Link>
        <Link
          to="/cases"
          className="rounded-sm border border-indigo-300 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-300/10"
        >
          All cases
        </Link>
      </div>

      <Card
        title="Recent cases"
        actions={
          <Link to="/cases" className="text-xs text-indigo-300 hover:underline">
            View all
          </Link>
        }
      >
        {cases.isLoading && <Spinner label="Loading cases" />}
        {cases.isError && (
          <p className="text-sm text-risk-high" role="alert">
            {cases.error instanceof ApiError
              ? cases.error.message
              : "Could not load cases."}
          </p>
        )}
        {cases.data && cases.data.length === 0 && (
          <EmptyState
            message="No cases yet."
            action={
              <Link
                to="/cases"
                className="text-sm font-medium text-indigo-300 hover:underline"
              >
                Create the first case
              </Link>
            }
          />
        )}
        {cases.data && cases.data.length > 0 && (
          <ul className="divide-y divide-navy-700">
            {cases.data.map((c) => (
              <li key={c.id}>
                <Link
                  to={`/cases/${c.id}`}
                  className="flex items-center justify-between gap-4 py-3 hover:bg-white/5"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-slate-200">
                      {c.title}
                    </div>
                    <div className="text-xs text-mute">
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
