/**
 * Auth state. The access + refresh tokens live in localStorage so a page
 * reload keeps the session; the API client attaches the access token and
 * rotates via /auth/refresh on a 401. (Cookie-based refresh would be nicer
 * but the backend issues bearer tokens.)
 */
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

import type { Role } from "../api/types";

/** localStorage, with an in-memory fallback for private-mode / SSR / tests
 * where `window.localStorage` is absent or throws. */
function safeStorage(): Storage {
  try {
    const ls = window.localStorage;
    const probe = "__aegis_probe__";
    ls.setItem(probe, probe);
    ls.removeItem(probe);
    return ls;
  } catch {
    const mem = new Map<string, string>();
    return {
      getItem: (k) => mem.get(k) ?? null,
      setItem: (k, v) => void mem.set(k, v),
      removeItem: (k) => void mem.delete(k),
      clear: () => mem.clear(),
      key: (i) => [...mem.keys()][i] ?? null,
      get length() {
        return mem.size;
      },
    } satisfies Storage;
  }
}

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  role: Role | null;
  email: string | null;
  setSession: (s: {
    accessToken: string;
    refreshToken: string;
    role: Role;
    email?: string | null;
  }) => void;
  setAccessToken: (token: string) => void;
  setEmail: (email: string) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      role: null,
      email: null,
      setSession: ({ accessToken, refreshToken, role, email = null }) =>
        set({ accessToken, refreshToken, role, email }),
      setAccessToken: (accessToken) => set({ accessToken }),
      setEmail: (email) => set({ email }),
      clear: () =>
        set({ accessToken: null, refreshToken: null, role: null, email: null }),
    }),
    { name: "aegis.auth", storage: createJSONStorage(safeStorage) },
  ),
);

export const isAuthenticated = () => useAuthStore.getState().accessToken !== null;
