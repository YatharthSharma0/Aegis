import { useEffect, useState } from "react";

/**
 * "Night" (the original dark forensic-ledger palette) and "day" (a white
 * background with green/blue accents; red is reserved for high/critical
 * risk in both modes). Applied as `data-theme` on `<html>` — see
 * `styles/tokens.css` for the token overrides.
 */
export type ThemeMode = "night" | "day";

const STORAGE_KEY = "aegis-theme";

function readStored(): ThemeMode | null {
  try {
    const v = window.localStorage.getItem(STORAGE_KEY);
    return v === "day" || v === "night" ? v : null;
  } catch {
    return null;
  }
}

function apply(theme: ThemeMode) {
  document.documentElement.setAttribute("data-theme", theme);
}

let current: ThemeMode = readStored() ?? "night";
const listeners = new Set<(theme: ThemeMode) => void>();

/** Call once, before the app renders, so there's no flash of the wrong theme. */
export function initTheme() {
  apply(current);
}

export function setTheme(theme: ThemeMode) {
  current = theme;
  apply(theme);
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private browsing / storage disabled — theme just won't persist.
  }
  listeners.forEach((listener) => listener(theme));
}

export function toggleTheme() {
  setTheme(current === "night" ? "day" : "night");
}

/** Subscribes a component to the current theme; updates on any toggle. */
export function useTheme(): ThemeMode {
  const [theme, setLocal] = useState<ThemeMode>(current);
  useEffect(() => {
    listeners.add(setLocal);
    return () => {
      listeners.delete(setLocal);
    };
  }, []);
  return theme;
}
