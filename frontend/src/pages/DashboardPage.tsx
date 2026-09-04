import { Link } from "react-router-dom";

import { Card } from "../ui/Card";
import { EmptyState } from "../ui/EmptyState";

export function DashboardPage() {
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-sm text-mute">
          Case overview and recent traces.
        </p>
      </header>
      <Card title="Recent cases">
        <EmptyState
          message="No cases yet. Case management lands in the next milestone."
          action={
            <Link
              to="/trace/new"
              className="text-sm font-medium text-indigo-300 hover:underline"
            >
              Start a trace
            </Link>
          }
        />
      </Card>
    </div>
  );
}
