from fastapi import APIRouter, HTTPException, Query

from app.repositories import staff as repo
from app.schemas.staff import Staff

router = APIRouter(prefix="/staff", tags=["personel"])


@router.get("", response_model=list[Staff], summary="Personel listesi")
async def listele(
    sadece_aktif: bool = Query(default=True, description="Ayrılan personeli gizle"),
) -> list[Staff]:
    return await repo.listele(sadece_aktif=sadece_aktif)


@router.get("/{staff_id}", response_model=Staff, summary="Personel künyesi")
async def getir(staff_id: int) -> Staff:
    if (satir := await repo.getir(staff_id)) is None:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    return satir
