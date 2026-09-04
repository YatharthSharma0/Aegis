/**
 * Fetch wrapper. Attaches the bearer token, normalises errors to `ApiError`
 * (with the backend's `error.code`), and transparently refreshes the access
 * token once on a 401 before giving up and clearing the session.
 */
import { useAuthStore } from "../state/authStore";
import type { TokenResponse } from "./types";

// Paths passed to this client already include the `/api/v1` prefix. In dev,
// vite proxies `/api` to the backend (see vite.config.ts); in prod set
// VITE_API_BASE_URL to the backend origin.
const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  signal?: AbortSignal;
}

async function raw(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.auth !== false) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  return fetch(`${BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    signal: opts.signal,
  });
}

let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const { refreshToken, setAccessToken, clear } = useAuthStore.getState();
  if (!refreshToken) return false;
  if (!refreshing) {
    refreshing = raw("/api/v1/auth/refresh", {
      method: "POST",
      auth: false,
      body: { refresh_token: refreshToken },
    })
      .then(async (res) => {
        if (!res.ok) {
          clear();
          return false;
        }
        const data = (await res.json()) as TokenResponse;
        useAuthStore.getState().setSession({
          accessToken: data.access_token,
          refreshToken: data.refresh_token,
          role: data.role as never,
        });
        setAccessToken(data.access_token);
        return true;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await raw(path, opts);
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new ApiError("backend_unavailable", "Cannot reach the server.", 0);
  }

  if (res.status === 401 && opts.auth !== false) {
    const ok = await tryRefresh();
    if (ok) res = await raw(path, opts);
  }

  if (res.status === 204) return undefined as T;

  let payload: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!res.ok) {
    const envelope = (payload as { error?: { code: string; message: string; details?: Record<string, unknown> } })?.error;
    if (res.status === 401) useAuthStore.getState().clear();
    throw new ApiError(
      envelope?.code ?? (res.status === 0 ? "backend_unavailable" : "http_error"),
      envelope?.message ?? res.statusText,
      res.status,
      envelope?.details,
    );
  }
  return payload as T;
}

export const get = <T,>(path: string, signal?: AbortSignal) =>
  api<T>(path, { signal });
export const post = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body });
export const patch = <T,>(path: string, body?: unknown) =>
  api<T>(path, { method: "PATCH", body });
