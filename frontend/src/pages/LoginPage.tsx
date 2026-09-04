import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../app/useAuth";
import { useAuthStore } from "../state/authStore";
import { Button } from "../ui/Button";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const authed = useAuthStore((s) => s.accessToken !== null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const dest = (location.state as { from?: string } | null)?.from ?? "/";
  if (authed) return <Navigate to={dest} replace />;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate(dest, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.code === "rate_limited") {
        setError("Too many attempts. Wait a minute and try again.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Invalid email or password.");
      } else if (err instanceof ApiError && err.code === "backend_unavailable") {
        setError("Cannot reach the server.");
      } else {
        setError("Sign-in failed. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded border border-navy-700 bg-navy-800/60 p-6"
      >
        <h1 className="text-lg font-bold tracking-tight">Aegis</h1>
        <p className="mb-6 text-xs uppercase tracking-widest text-mute">
          Investigator sign-in
        </p>

        <label className="mb-1 block text-xs text-mute" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="mb-4 w-full rounded-sm border border-navy-600 bg-navy-900 px-3 py-2 text-sm outline-none focus:border-indigo-300"
        />

        <label className="mb-1 block text-xs text-mute" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="mb-5 w-full rounded-sm border border-navy-600 bg-navy-900 px-3 py-2 text-sm outline-none focus:border-indigo-300"
        />

        {error && (
          <p role="alert" className="mb-4 text-sm text-risk-high">
            {error}
          </p>
        )}

        <Button type="submit" loading={busy} className="w-full">
          Sign in
        </Button>
      </form>
    </div>
  );
}
