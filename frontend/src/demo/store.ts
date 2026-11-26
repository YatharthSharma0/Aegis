/** Demo state, kept in memory and mirrored to localStorage so edits survive a reload. */
import { seedState, type DemoState } from "./seed";

const KEY = "aegis.demo.v1";

let state: DemoState | null = null;

function read(): DemoState | null {
  try {
    const saved = window.localStorage.getItem(KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as DemoState;
    const lists = [parsed.cases, parsed.complaints, parsed.runs, parsed.audit];
    return lists.every(Array.isArray) ? parsed : null;
  } catch {
    return null;
  }
}

export function demoState(): DemoState {
  if (!state) {
    state = read() ?? seedState();
    saveDemoState();
  }
  return state;
}

export function saveDemoState(): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // Storage blocked or full: the demo still works until the page reloads.
  }
}

/** Throw away every edit and start again from the sample data. */
export function resetDemoState(): void {
  state = seedState();
  saveDemoState();
}
