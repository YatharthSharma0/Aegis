export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-mute" role="status">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-indigo-300 border-t-transparent"
        aria-hidden
      />
      {label}
    </div>
  );
}
