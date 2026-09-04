export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted" role="status">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-link border-t-transparent"
        aria-hidden
      />
      {label}
    </div>
  );
}
