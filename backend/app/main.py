from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin, auth, manager, master, public


app = FastAPI(title="Zenail CRM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(master.router, prefix="/api")
app.include_router(manager.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"ok": True}

