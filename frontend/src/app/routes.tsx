import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AdminAuditPage } from "../pages/AdminAuditPage";
import { CaseDetailPage } from "../pages/CaseDetailPage";
import { CasesPage } from "../pages/CasesPage";
import { DashboardPage } from "../pages/DashboardPage";
import { LandingPage } from "../pages/LandingPage";
import { LoginPage } from "../pages/LoginPage";
import { NewTracePage } from "../pages/NewTracePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ReportPage } from "../pages/ReportPage";
import { TraceResultPage } from "../pages/TraceResultPage";
import { useAuthStore } from "../state/authStore";
import { AppShell } from "./AppShell";

/**
 * Everything under AppShell is auth-gated; /login and the root path (when
 * signed out) are the public routes. The root check happens here, inline,
 * rather than via a redirect, so a signed-out visit to "/" renders the
 * marketing landing page instead of bouncing to /login.
 */
function Protected() {
  const authed = useAuthStore((s) => s.accessToken !== null);
  const location = useLocation();

  if (!authed) {
    if (location.pathname === "/") return <LandingPage />;
    return (
      <Navigate to="/login" replace state={{ from: location.pathname }} />
    );
  }

  return (
    <AppShell>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:id" element={<CaseDetailPage />} />
        <Route path="trace/new" element={<NewTracePage />} />
        <Route path="trace/:id" element={<TraceResultPage />} />
        <Route path="trace/:id/report" element={<ReportPage />} />
        <Route path="admin/audit" element={<AdminAuditPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AppShell>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/*" element={<Protected />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
