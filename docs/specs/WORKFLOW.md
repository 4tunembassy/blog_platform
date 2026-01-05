# Workflow for Low-Breakage Delivery

## 1) Branching model
- `main` = always deployable
- `develop` (optional) = integration branch if you want
- `feature/<epic>-<short-name>` = work branches

Recommended (simplest): **trunk-based with short-lived feature branches**.

## 2) Definition of Done for every PR
A PR is "done" only if:
- builds locally
- `backend/api` starts and returns `/healthz`
- infra docker starts (postgres + redis)
- no lint errors (when configured)
- changes are documented in `docs/PROJECT_STATE.md`

## 3) Continuity anchor (anti-chat-breakage)
We treat `docs/PROJECT_STATE.md` as the single continuity file.

Whenever a chat breaks or you open a new chat:
- paste the entire `docs/PROJECT_STATE.md` content
- paste the last error trace
- paste the last command you ran

This prevents restarting from scratch.

## 4) Architecture decision records (ADRs)
Every non-trivial decision gets a one-page ADR under `docs/adr/`:
- why we decided it
- options considered
- consequences

## 5) Release discipline
- Tag working milestones: `v0.1.0`, `v0.2.0`...
- Never hot-edit production: deploy only tagged images/builds.
