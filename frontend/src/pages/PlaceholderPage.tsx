import { EmptyState } from "../ui/EmptyState";

/** Stand-in for a route whose screen ships in a later Phase 3 PR. */
export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-xl font-bold tracking-tight">{title}</h1>
      <EmptyState message="This screen is not built yet — it arrives in a later milestone." />
    </div>
  );
}
