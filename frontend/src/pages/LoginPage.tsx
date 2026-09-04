import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../api/client";
import { useAuth } from "../app/useAuth";
import { useAuthStore } from "../state/authStore";
import { Button } from "../ui/Button";
import { textInputClass } from "../ui/inputClass";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const authed = useAuthStore((s) => s.accessToken !== null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <form
        onSubmit={submit}
        className="w-full max-w-[420px] rounded-sm border border-subtle bg-raised p-6"
      >
        <div className="mb-6 flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center border-2 border-brand text-xs font-semibold text-brand">
            Æ
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-primary">Aegis</h1>
            <p className="text-xs uppercase tracking-widest text-muted">
              Investigator sign-in · SIH26183
            </p>
          </div>
        </div>

        <label className="mb-1 block text-xs text-muted" htmlFor="email">
          Official email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className={textInputClass("mb-4")}
        />

        <label className="mb-1 block text-xs text-muted" htmlFor="password">
          Password
        </label>
        <div className="relative mb-5">
          <input
            id="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className={textInputClass("pr-10")}
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 flex w-9 items-center justify-center text-muted hover:text-secondary"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>

        {error && (
          <p role="alert" className="mb-4 text-sm text-risk-high">
            {error}
          </p>
        )}

        <Button type="submit" loading={busy} className="w-full">
          Sign in
        </Button>

        <p className="mt-4 text-[11px] leading-snug text-muted">
          Restricted access · Law-enforcement use only · No public sign-up
        </p>
      </form>
    </div>
  );
}
