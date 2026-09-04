import { CloudOff, RefreshCw, TriangleAlert } from "lucide-react";

import { ApiError } from "../api/client";

/** Consistent error panel. Names the backend-unreachable case explicitly
 * (Style Guide: a dropped backend is a state, not a stack trace). */
export function ErrorState({
  error,
  onRetry,
  context = "load this",
}: {
  error: unknown;
  onRetry?: () => void;
  context?: string;
}) {
  const offline =
    error instanceof ApiError &&
    (error.code === "backend_unavailable" || error.status === 0);
  const notFound = error instanceof ApiError && error.status === 404;

  const message = offline
    ? "Can't reach the Aegis backend. It may be starting up or offline — your work is not lost."
    : notFound
      ? "That record does not exist."
      : error instanceof ApiError
        ? error.message
        : `Something went wrong trying to ${context}.`;

  const Icon = offline ? CloudOff : TriangleAlert;

  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-sm border border-dashed border-strong px-6 py-8 text-center"
    >
      <Icon size={22} className={offline ? "text-muted" : "text-risk-high"} aria-hidden />
      <p className="max-w-sm text-sm text-secondary">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 rounded-sm border border-subtle px-3 py-1.5 text-xs text-secondary transition-colors duration-fast hover:bg-hover hover:text-primary"
        >
          <RefreshCw size={13} aria-hidden />
          Try again
        </button>
      )}
    </div>
  );
}
