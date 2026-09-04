import { FileText, FolderOpen, LayoutDashboard, LogOut, Search } from "lucide-react";
import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { cn } from "../ui/cn";
import { useAuth } from "./useAuth";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/cases", label: "Cases", icon: FolderOpen },
  { to: "/trace/new", label: "New trace", icon: Search },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { email, role, logout } = useAuth();

  return (
    <div className="grid min-h-screen grid-cols-[220px_1fr]">
      <aside className="flex flex-col border-r border-navy-700 bg-navy-900 p-3">
        <div className="mb-6 px-2 pt-2">
          <div className="text-lg font-bold tracking-tight">Aegis</div>
          <div className="text-[11px] uppercase tracking-widest text-mute">
            SIH26183
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-sm",
                  isActive
                    ? "bg-indigo-500/15 text-indigo-300"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200",
                )
              }
            >
              <Icon size={18} aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-navy-700 pt-3">
          {role === "admin" && (
            <NavLink
              to="/admin/audit"
              className="mb-1 flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-sm text-slate-400 hover:bg-white/5 hover:text-slate-200"
            >
              <FileText size={18} aria-hidden />
              Audit log
            </NavLink>
          )}
          <div className="px-2.5 pb-2 text-xs text-mute">
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
      <main className="min-w-0 overflow-y-auto px-6 py-6">{children}</main>
    </div>
  );
}
