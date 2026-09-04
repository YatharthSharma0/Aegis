import { Navigate, Route, Routes } from "react-router-dom";

import { CaseDetailPage } from "../pages/CaseDetailPage";
import { CasesPage } from "../pages/CasesPage";
import { DashboardPage } from "../pages/DashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { NewTracePage } from "../pages/NewTracePage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";
import { TraceResultPage } from "../pages/TraceResultPage";
import { AppShell } from "./AppShell";
import { RequireAuth } from "./RequireAuth";

/** Everything under AppShell is auth-gated; /login is the only public route. */
function Protected() {
  return (
    <RequireAuth>
      <AppShell>
        <Routes>
          <Route index element={<DashboardPage />} />
          <Route path="cases" element={<CasesPage />} />
          <Route path="cases/:id" element={<CaseDetailPage />} />
          <Route path="trace/new" element={<NewTracePage />} />
          <Route path="trace/:id" element={<TraceResultPage />} />
          <Route
            path="trace/:id/report"
            element={<PlaceholderPage title="Report" />}
          />
          <Route path="admin/audit" element={<PlaceholderPage title="Audit log" />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AppShell>
    </RequireAuth>
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
