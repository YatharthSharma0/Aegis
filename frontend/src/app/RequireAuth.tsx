import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuthStore } from "../state/authStore";

/** Gate a route on a stored access token; bounce to /login otherwise,
 * remembering where the user was headed. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const authed = useAuthStore((s) => s.accessToken !== null);
  const location = useLocation();
  if (!authed) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
