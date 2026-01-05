# Backend API (FastAPI)

## Purpose
HTTP API for admin + site (content queries, auth, approvals) and for triggering workflows.

## Run (local)
1. Create venv
2. Install requirements
3. Run: `uvicorn app.main:app --reload --port 8000`

## Endpoints (MVP)
- `GET /healthz`
- `GET /readyz`
