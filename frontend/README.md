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
