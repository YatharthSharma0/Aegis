import { CloudOff, FileText, FolderOpen, LayoutDashboard, LogOut, Search } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";

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
    "flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-sm",
    isActive
      ? "bg-indigo-500/15 text-indigo-300"
      : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
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
    <div className="flex min-h-screen flex-col md:grid md:grid-cols-[220px_1fr]">
      <aside className="flex flex-col border-b border-navy-700 bg-navy-900 p-3 md:border-b-0 md:border-r">
        <div className="mb-4 px-2 pt-1 md:mb-6 md:pt-2">
          <div className="text-lg font-bold tracking-tight">Aegis</div>
          <div className="text-[11px] uppercase tracking-widest text-mute">
            SIH26183
          </div>
        </div>
        <nav className="flex flex-1 flex-row flex-wrap gap-1 md:flex-col">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navItemClass}>
              <Icon size={18} aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-2 border-navy-700 pt-2 md:mt-0 md:border-t md:pt-3">
          {role === "admin" && (
            <NavLink to="/admin/audit" className={navItemClass}>
              <FileText size={18} aria-hidden />
              Audit log
            </NavLink>
          )}
          <div className="hidden px-2.5 pb-2 pt-1 text-xs text-mute md:block">
            <div className="truncate" title={email ?? undefined}>
              {email ?? "signed in"}
            </div>
            <div className="uppercase tracking-wide">{role}</div>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2.5 rounded-sm px-2.5 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200"
          >
            <LogOut size={18} aria-hidden />
            Sign out
          </button>
        </div>
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
  );
}
