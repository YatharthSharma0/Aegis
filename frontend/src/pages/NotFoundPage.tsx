import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-md space-y-3 py-16 text-center">
      <p className="text-xs uppercase tracking-widest text-muted">404</p>
      <h1 className="text-xl font-bold tracking-tight text-primary">Page not found</h1>
      <p className="text-sm text-muted">
        The page you asked for does not exist.
      </p>
      <Link
        to="/"
        className="inline-block text-sm font-medium text-link hover:underline"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
