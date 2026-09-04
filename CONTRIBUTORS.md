# Contributors

Aegis is built by a six-person Smart India Hackathon 2026 team. Each member owns a
clearly-defined area and commits from their own GitHub account, so the repository
history is an honest record of distributed work.

> **⚠️ Five of the six rows below are placeholders** carried over from the design
> vault so this file reads coherently. **Known open Phase 0 item** — replace each
> with the real member's name and GitHub handle before the internal hackathon,
> keeping the role shape. The Team Lead row is the real contributor; the repo has
> a single real contributor so far.

| Role | Name | GitHub | Primary ownership |
|---|---|---|---|
| Team Lead / Full-Stack Integrator | Yatharth Sharma | [@YatharthSharma0](https://github.com/YatharthSharma0) | Architecture decisions, FE↔BE integration, API contracts, Git workflow, case-management module |
| Blockchain & Backend Engineer | _Nikhil_ | `@—` | Data-provider integration, graph engine (walk + taint), clustering heuristics, DB schema, attribution logic |
| AI / ML Engineer | _Sara_ | `@—` | GNN typology/risk model, NLP complaint extraction, grounded LLM report generation, embeddings/similarity, model evaluation |
| Frontend & UI/UX Engineer | _Kabir_ | `@—` | React app, live graph canvas (Cytoscape), design system, all screens, WebSocket client |
| Domain Researcher & Data Curator | _Meera_ | `@—` | Official PS reconciliation, India VASP TagPack, demo scenarios, legal/regulatory accuracy, case studies |
| Presentation, DevOps & QA Lead | _Dev_ | `@—` | Pitch deck, demo script + rehearsal, deployment/hosting, environment stability, end-to-end testing, backup video |

## Working agreement

- **Branching:** `feature/<area>-<short-desc>` per task. Small PRs, reviewable in ~10 minutes.
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) — `type(scope): summary`
  (`feat fix refactor test docs chore perf build ci`). Logical units, not "wip" blobs.
- **`main` is protected:** no direct pushes (enforced for admins too), CI must pass,
  linear history. Required approving reviews are **0 for now** (a single contributor
  cannot approve their own PR) and rise to **1** once real collaborators are added.
  Configured in GitHub repo settings (Settings → Branches) — see `docs/validation.md`.
- **Secrets:** never committed. `backend/.env.example` and `frontend/.env.example` are the
  single source of truth for configuration keys.
- **Definition of Done:** implementation matches the design, `./scripts/validate.sh` passes,
  tests exist for new behaviour, docs updated when interfaces change.

## Co-authoring

For genuine pair work, credit both with a trailer:

```
Co-authored-by: Real Name <email@example.com>
```
