# Aegis

**The investigator's shield against crypto fraud.**

Aegis turns a victim-reported cryptocurrency wallet address into an evidence-grade,
exchange-attributed, laundering-aware investigation lead in minutes instead of days.

Built for **Smart India Hackathon 2026**, problem statement
[**SIH26183**](https://sih.gov.in/sih2026PS) — *Real-Time Identification of
Fraud-Linked Cryptocurrency Exchanges from Victim-Reported Suspect Wallet Addresses
through Automated Blockchain Analytics* (Ministry of Home Affairs · Indian Cyber
Crime Coordination Centre, I4C / CIS Division).

> Assistive, not autonomous. Aegis produces leads and draft notices for a human
> officer to review and sign off. It never freezes funds, signs transactions, or
> connects user wallets — it only *reads* public blockchain data and *reports*.

---

## What it does

An officer submits a scam victim's wallet address (or the raw complaint text).
Aegis:

1. extracts the structured facts (address, chain, amount, timestamp) from the complaint,
2. traces the funds forward on the public blockchain, hop by hop, on a live graph,
3. clusters related wallets and flags laundering typologies (peel chains, mixers, bridges, fan-out),
4. names the **exchange / VASP** receiving the funds, with a transparent confidence score,
5. generates a standardized investigation report that drops into the NCRP / SAHYOG workflow.

## Architecture (target)

| Layer | Stack |
|---|---|
| Backend | Python 3.12 · FastAPI (modular monolith) · Celery + Redis (async, later phase) |
| Graph / data | Neo4j (graph) · PostgreSQL + pgvector (relational / audit / similarity) — later phases |
| Frontend | React 18 · Vite · TypeScript · Tailwind · Cytoscape.js graph canvas |
| AI/ML | GraphSAGE GNN (laundering typology + risk) · NLP complaint extraction · grounded LLM report generation |

The current repository is **Phase 0** — foundation only (see below). Persistence,
workers, the tracing engine, and the AI components are built in later phases per
the execution plan.

## Repository layout

```
backend/    FastAPI application (Phase 0: health endpoint + test + tooling)
frontend/   Vite + React + TypeScript app (Phase 0: skeleton shell)
docs/       Data licences, validation guide
scripts/    validate.sh — the single local check gate
.github/    CI pipeline
CLAUDE.md   Operating manual for AI coding agents on this repo
MEMORY.md   Living record of actual implementation state
```

## Getting started

Prerequisites: [`uv`](https://docs.astral.sh/uv/) (manages Python 3.12), Node 20+, and
optionally Docker with Compose.

```bash
# Backend
cd backend
uv sync                       # creates .venv with Python 3.12 + deps
uv run uvicorn app.main:app --reload   # http://localhost:8000  (/health, /docs)

# Frontend
cd frontend
npm install
npm run dev                    # http://localhost:5173

# Or everything at once
docker compose up --build
```

## Validation

One command runs every check CI runs:

```bash
./scripts/validate.sh
```

Backend: `ruff` + `mypy` + `pytest`. Frontend: `eslint` + `tsc` + `vite build` + `vitest`.

## Contributing

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md). Conventional Commits, small logical units,
`main` is protected (PRs + green CI). Never commit secrets — `.env.example` files
are the single source of truth for configuration.

## Licence

[MIT](LICENSE). Third-party dataset and label-set licences are tracked in
[`docs/DATA_LICENSES.md`](docs/DATA_LICENSES.md).
