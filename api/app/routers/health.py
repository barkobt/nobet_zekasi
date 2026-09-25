from fastapi import APIRouter

from app.repositories import health as repo
from app.schemas.staff import HealthCheck

router = APIRouter(tags=["sistem"])


@router.get("/health", response_model=HealthCheck, summary="Servis ve veritabanı durumu")
async def saglik() -> HealthCheck:
    try:
        satir = await repo.kontrol()
    except Exception as hata:  # noqa: BLE001 — health endpoint'i asla 500 vermemeli
        return HealthCheck(status="hata", db=False, detay=str(hata))
    return HealthCheck(status="ok", db=True, **satir)
