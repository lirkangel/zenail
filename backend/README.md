# Zenail Backend

Backend API cho Zenail, build bằng FastAPI + SQLAlchemy + Alembic + PostgreSQL.

## Yêu cầu

- Python >= 3.11
- PostgreSQL 16+ (nếu chạy ngoài Docker)
- Khuyến nghị dùng `uv` để quản lý env/deps

## Cấu hình môi trường

```bash
cp .env.example .env
```

Biến quan trọng:

- `DATABASE_URL`: ví dụ `postgresql+psycopg://zenail:zenail@localhost:5432/zenail`
- `JWT_SECRET`: secret để ký JWT
- `JWT_EXPIRES_MINUTES`: thời gian hết hạn JWT (phút)
- `CORS_ORIGINS`: danh sách origin cho frontend (phân tách bằng dấu phẩy)

## Chạy local (không dùng Docker)

```bash
uv sync
uv run uvicorn app.main:app --reload
```

API chạy mặc định ở `http://localhost:8000` và Swagger ở `http://localhost:8000/docs`.

## Tests

```bash
uv run pytest
```

## Migrations (Alembic)

```bash
uv run alembic upgrade head
```

## Seed dữ liệu demo

```bash
uv run python -m app.scripts.seed
```

## Chạy bằng Docker (từ repo root)

```bash
docker compose up --build
```

Seed sau khi container đã lên:

```bash
docker compose exec backend uv run python -m app.scripts.seed
```
