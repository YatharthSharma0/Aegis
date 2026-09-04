import { CloudOff, FileText, FolderOpen, LayoutDashboard, LogOut, Search } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { ThemeToggle } from "../components/ThemeToggle";
import { useHealth } from "../features/system/useHealth";
import { cn } from "../ui/cn";
import { useAuth } from "./useAuth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/cases", label: "Cases", icon: FolderOpen },
  { to: "/trace/new", label: "New trace", icon: Search },
];

const navItemClass = ({ isActive }: { isActive: boolean }) =>
  cn(
    "flex items-center gap-2.5 border-l-[3px] px-2.5 py-2 text-sm transition-colors duration-fast",
    isActive
      ? "border-brand bg-hover font-medium text-primary"
      : "border-transparent text-secondary hover:bg-hover hover:text-primary",
  );

export function AppShell({ children }: { children: ReactNode }) {
  const { email, role, logout } = useAuth();
  const { offline } = useHealth();
  const location = useLocation();
  const mainRef = useRef<HTMLElement | null>(null);

  // Move focus to the content region on navigation so keyboard and
  // screen-reader users aren't stranded at the top of the nav.
  useEffect(() => {
    mainRef.current?.focus();
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-14 flex-none items-center gap-4 border-b border-subtle bg-raised px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center border-2 border-brand text-[11px] font-semibold text-brand">
            Æ
          </span>
          <span className="text-base font-semibold tracking-tight text-primary">
            Aegis
          </span>
        </div>
        <span className="hidden text-xs uppercase tracking-widest text-muted sm:inline">
          SIH26183
        </span>
        <div className="flex-1" />
        <span
          className="inline-flex items-center gap-1.5 rounded-sm border border-strong px-2 py-0.5 text-xs font-medium text-secondary"
          title="This deployment reads live blockchain data — no demo fixtures"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-success" aria-hidden />
          Live
        </span>
        <ThemeToggle />
        <div className="hidden text-right text-xs text-muted sm:block">
          <div className="max-w-[16ch] truncate" title={email ?? undefined}>
            {email ?? "signed in"}
          </div>
          <div className="uppercase tracking-wide">{role}</div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-1.5 rounded-sm border border-subtle px-2.5 py-1.5 text-xs text-secondary transition-colors duration-fast hover:bg-hover hover:text-primary"
        >
          <LogOut size={14} aria-hidden />
          Sign out
        </button>
      </header>

      <div className="flex flex-1 flex-col md:flex-row">
        <aside className="flex flex-none flex-col border-b border-subtle bg-base py-2 md:w-[232px] md:border-b-0 md:border-r md:py-4">
          <nav className="flex flex-row flex-wrap gap-1 md:flex-col md:gap-0.5">
            {NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink key={to} to={to} end={end} className={navItemClass}>
                <Icon size={18} aria-hidden />
                {label}
              </NavLink>
            ))}
          </nav>
          {role === "admin" && (
            <>
              <div className="mx-3 mt-3 hidden border-t border-subtle pt-3 text-[11px] font-semibold uppercase tracking-widest text-muted md:block">
                Administration
              </div>
              <nav className="flex flex-row flex-wrap gap-1 md:flex-col md:gap-0.5">
                <NavLink to="/admin/audit" className={navItemClass}>
                  <FileText size={18} aria-hidden />
                  Audit log
                </NavLink>
              </nav>
            </>
          )}
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          {offline && (
            <div
              role="alert"
              className="flex items-center gap-2 border-b border-risk-high/40 bg-risk-high/10 px-6 py-2 text-sm text-risk-high"
            >
              <CloudOff size={15} aria-hidden />
              Backend unreachable — showing last-known data. Retrying automatically.
            </div>
          )}
          <main
            ref={mainRef}
            tabIndex={-1}
            className="min-w-0 flex-1 overflow-y-auto px-4 py-6 outline-none sm:px-6"
          >
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
