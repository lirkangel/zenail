# Zenail Frontend

Frontend web cho Zenail (guest booking + staff area), build bằng React + Vite + TypeScript.

## Yêu cầu

- Node.js (khuyến nghị Node 22 để khớp với `docker-compose.yml`)

## Cấu hình môi trường

```bash
cp .env.example .env
```

Biến quan trọng:

- `VITE_API_BASE_URL`: base URL của backend (mặc định `http://localhost:8000`)

## Chạy local (không dùng Docker)

```bash
npm install
npm run dev
```

Mặc định Vite chạy ở `http://localhost:5173`.

## Lint / Build / Preview

```bash
npm run lint
npm run build
npm run preview
```

## Chạy bằng Docker (từ repo root)

```bash
docker compose up --build
```
