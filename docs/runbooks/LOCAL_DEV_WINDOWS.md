# Local Dev Runbook (Windows) — Office/Home

## 1) One-time prerequisites
- Git
- Node.js LTS + pnpm
- Python 3.11+
- Docker Desktop (WSL2)

## 2) Clone and sync
```powershell
git clone <YOUR_GITHUB_REPO_URL>
cd <REPO>
```

Use one branch per task:
```powershell
git checkout -b feature/epic-1-1-db-foundation
```

## 3) Start infra (Postgres + Redis)
From repo root:
```powershell
cd infra\docker
docker compose -f docker-compose.local.yml up -d
```

## 4) Backend API
```powershell
cd ..\..\backend\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## 5) Worker (placeholder)
Open a new terminal:
```powershell
cd backend\worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip
python -m worker.run
```

## 6) Frontend web/admin scaffolds
We keep `frontend/web` and `frontend/admin` as separate Next.js apps for clean traceability.

Web:
```powershell
cd frontend\web
pnpm dlx create-next-app@latest . --ts --eslint --app --tailwind --src-dir --import-alias "@/*"
pnpm dev
```

Admin:
```powershell
cd ..\admin
pnpm dlx create-next-app@latest . --ts --eslint --app --tailwind --src-dir --import-alias "@/*"
pnpm dev --port 3001
```

## 7) Continuity discipline (important)
At end of each session:
1. Update `docs/PROJECT_STATE.md`
2. Commit small:
```powershell
git add -A
git commit -m "feat: ..."
git push -u origin HEAD
```
