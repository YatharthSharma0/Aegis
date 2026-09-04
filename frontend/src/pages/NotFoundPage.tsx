import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-md space-y-3 py-16 text-center">
      <p className="text-xs uppercase tracking-widest text-mute">404</p>
      <h1 className="text-xl font-bold tracking-tight">Page not found</h1>
      <p className="text-sm text-mute">
        The page you asked for does not exist.
      </p>
      <Link
        to="/"
        className="inline-block text-sm font-medium text-indigo-300 hover:underline"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
