import { Link } from "react-router-dom";

import { CaseStatusBadge } from "../components/CaseStatusBadge";
import { ErrorState } from "../components/ErrorState";
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
        <h1 className="text-xl font-bold tracking-tight text-primary">Dashboard</h1>
        <p className="text-sm text-muted">Recent cases and quick actions.</p>
      </header>

      <div className="flex gap-2">
        <Link
          to="/trace/new"
          className="rounded-sm bg-brand px-4 py-2 text-sm font-medium text-ink hover:bg-brand-hover"
        >
          New trace
        </Link>
        <Link
          to="/cases"
          className="rounded-sm border border-strong px-4 py-2 text-sm font-medium text-secondary hover:bg-hover hover:text-primary"
        >
          All cases
        </Link>
      </div>

      <Card
        title="Recent cases"
        actions={
          <Link to="/cases" className="text-xs text-link hover:underline">
            View all
          </Link>
        }
      >
        {cases.isLoading && <Spinner label="Loading cases" />}
        {cases.isError && (
          <ErrorState error={cases.error} onRetry={() => cases.refetch()} context="load cases" />
        )}
        {cases.data && cases.data.length === 0 && (
          <EmptyState
            message="No cases yet."
            action={
              <Link
                to="/cases"
                className="text-sm font-medium text-link hover:underline"
              >
                Create the first case
              </Link>
            }
          />
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
