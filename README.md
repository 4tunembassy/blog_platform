# Governed AI Blog/News Platform (MVP)

This repo is optimized for **traceability**, **continuity** (office ↔ home), and **low-breakage** delivery.

## Folders

- `backend/` — FastAPI API + worker pipeline (Python)
- `frontend/` — public site + admin (Next.js)
- `infra/` — Docker, DB schema, reverse proxy configs
- `docs/` — runbooks, specs, ADRs (architecture decision records)
- `scripts/` — helper scripts

## Continuity workflow (office ↔ home)

- Work in small PR-sized commits.
- Push to GitHub at the end of every work session.
- Pull before starting a new session on any machine.

## What to paste into a new chat if we ever lose context

Open `docs/PROJECT_STATE.md` and paste:
- Current milestone/epic
- Last successful command + output
- Any error trace
- Current `.env` differences (no secrets)

That single file is our continuity anchor.
