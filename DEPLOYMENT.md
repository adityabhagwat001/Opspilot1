# OpsPilot Deployment Guide

This guide covers deploying OpsPilot across local environments, Docker Compose, and cloud containers.

---

## 1. Local Production-Mode Deployment

### Backend
```powershell
# Set production environment variables
$env:ENVIRONMENT = "production"
$env:SECRET_KEY = "your-32-character-secret-key"
$env:OPSPILOT_APPROVAL_SECRET = "your-approval-boundary-secret-key"

# Run Uvicorn production server
.\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --workers 4 --app-dir backend
```

### Frontend
```powershell
cd frontend
npm run build
# Serve dist folder via NGINX, Caddy, or serve
npx serve -s dist -l 5173
```

---

## 2. Docker Compose Deployment

The provided `docker-compose.yml` spins up:
1. PostgreSQL 16 Alpine container with healthchecks
2. OpsPilot FastAPI Backend container
3. OpsPilot React Frontend container

### Run:
```bash
docker compose up -d --build
```

### Access:
- Frontend: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/docs`

---

## 3. Environment Variables Reference

| Variable | Description | Default (Dev) |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite+aiosqlite:///./opspilot_system.db` |
| `OPS_DATABASE_URL` | Target operations database | `sqlite+aiosqlite:///./operational_data.db` |
| `SECRET_KEY` | JWT signing secret | 32-character key |
| `OPSPILOT_APPROVAL_SECRET` | HMAC secret for write tokens | 32-character key |
| `GITHUB_TOKEN` | Fine-grained GitHub PAT | Optional |
| `LLM_PROVIDER` | LLM model provider (`openai`, `anthropic`, `ollama`) | `openai` |
