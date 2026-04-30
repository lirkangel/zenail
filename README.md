# Zenail CRM

Mobile-first CRM for a multi-branch nail salon.

## Local dev (Docker)

Prereqs: Docker Desktop.

1. Copy env files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

2. Start everything:

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000` (docs at `/docs`)
- Postgres: `localhost:5432`

## Seed data

Once containers are up, seed the DB:

```bash
docker compose exec backend uv run python -m app.scripts.seed
```

### Demo accounts

- Admin: `admin@zenail.local` / `admin123`
- Manager (Branch A): `manager.a@zenail.local` / `manager123`
- Manager (Branch B): `manager.b@zenail.local` / `manager123`
- Master: use any `master.*@zenail.local` / `master123`

## Backend dev (uv)

If you want to run the backend without Docker:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

