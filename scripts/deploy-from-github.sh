#!/usr/bin/env bash
set -euo pipefail

echo "[deploy] Starting Zenail deploy at $(date)"
cd /opt/zenail

git fetch origin main --depth=1
git reset --hard origin/main
echo "[deploy] Synced /opt/zenail to origin/main"

# git reset doesn't remove untracked folders from previous runs
rm -rf .venv || true
find . -type d -name "__pycache__" -prune -exec rm -rf {} + || true
echo "[deploy] Cleaned .venv and __pycache__"

FRONTEND_PORT="${FRONTEND_PORT:-3002}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
PUBLIC_API_BASE_URL="${PUBLIC_API_BASE_URL:-http://10.0.0.11:8001}"
CORS_ORIGINS="${CORS_ORIGINS:-http://10.0.0.11:3002,http://localhost:3002}"

FRONTEND_PORT="$FRONTEND_PORT" \
BACKEND_PORT="$BACKEND_PORT" \
PUBLIC_API_BASE_URL="$PUBLIC_API_BASE_URL" \
CORS_ORIGINS="$CORS_ORIGINS" \
docker compose up -d --build
echo "[deploy] Docker Compose stack is up"

docker compose exec -T backend uv run alembic upgrade head
docker compose exec -T backend uv run python -m app.scripts.seed
echo "[deploy] Migrated and seeded"

echo "[deploy] Done at $(date)"

