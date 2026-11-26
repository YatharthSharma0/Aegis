/**
 * Data mode, fixed at build time by `VITE_DATA_MODE`.
 *
 * `demo` (the default) answers every API call in the browser from synthetic
 * sample data, so the app can be showcased with no backend. `live` talks to the
 * real FastAPI backend.
 */
export const DEMO_MODE = import.meta.env.VITE_DATA_MODE !== "live";
