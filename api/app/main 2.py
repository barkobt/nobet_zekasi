"""Nöbet Zekâsı API — Acıbadem Smart Planner.

Katmanlar: routers/ (HTTP) → repositories/ (SQL). schemas/ yalnızca API sözleşmesi.
Veritabanının zaten uyguladığı kurallar burada tekrarlanmaz; hata yakalanıp çevrilir.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request

from app.db import close_pool, open_pool
from app.routers import health, staff
from app.settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await open_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Nöbet Zekâsı API",
    description="Acıbadem Kent ASG acil servisi nöbet planlama servisi.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def demo_token_kontrolu(request: Request, call_next):
    """Demo erişimi: web'in sunucu tarafı proxy'si bu token'ı gönderir, tarayıcı görmez.

    Token boşsa doğrulama kapalıdır (yerel geliştirme). /health ve dokümantasyon
    her zaman açıktır: Railway sağlık kontrolü ve openapi-typescript'in erişmesi gerekir.
    """
    token = get_settings().demo_api_token
    acik_yollar = ("/api/health", "/openapi.json", "/docs", "/redoc")
    if token and not request.url.path.startswith(acik_yollar):
        if request.headers.get("x-demo-token") != token:
            raise HTTPException(status_code=401, detail="Geçersiz demo anahtarı.")
    return await call_next(request)


app.include_router(health.router, prefix="/api")
app.include_router(staff.router, prefix="/api")
