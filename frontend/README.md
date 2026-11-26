# Aegis frontend

React 18 · Vite · TypeScript · Tailwind CSS. Later phases add the Cytoscape.js
fund-flow graph, the design system, and the trace screens.

## Setup

```bash
npm install
cp .env.example .env      # optional; defaults work for local dev
```

## Run

```bash
npm run dev               # http://localhost:5173  (/api proxied to :8000)
```

## Data mode

`VITE_DATA_MODE` is read at build time.

| Value | Behaviour |
|---|---|
| `demo` (default) | No backend. `src/demo/server.ts` answers the API client from sample data kept in `localStorage`. |
| `live` | Calls the FastAPI backend (Docker Compose sets this). |

When you add or change a backend endpoint the UI uses, add it to
`src/demo/server.ts` too.

## Checks

```bash
npm run lint              # eslint (flat config)
npm run build             # tsc -b + vite build
npm run test              # vitest (jsdom)
```

## Layout

```
src/
  main.tsx        React entry
  App.tsx         root component (Phase 0: placeholder shell)
  index.css       Tailwind entry
  setupTests.ts   jest-dom matchers for vitest
```
