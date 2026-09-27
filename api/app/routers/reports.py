"""Raporlar ekranı (E-11). Çizelge Excel'inden çıkarılan Özet ve Eksikler
buraya taşındı; hesaplar app/rapor.py'de tek yerde duruyor."""

from datetime import timedelta

from fastapi import APIRouter, HTTPException

from app import rapor
from app.repositories import schedule as repo
from app.routers.export import _donem_etiketi
from app.schemas.reports import PersonSummary, Report, Shortfall

router = APIRouter(tags=["raporlar"])


@router.get("/drafts/{draft_id}/report", response_model=Report, summary="Kişi özeti + eksikler")
async def rapor_getir(draft_id: int) -> Report:
    if (t := await repo.taslak(draft_id)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")

    bas, bitis = t["period_start"], t["period_end"]        # bitis DIŞLAYICI
    veri = await repo.cizelge_verisi(draft_id, bas, bitis - timedelta(days=1))

    return Report(
        draft_id=t["id"],
        draft_name=t["name"],
        unit_name=t["unit_name"],
        status=t["status"],
        period_start=bas,
        period_end=bitis,
        period_label=_donem_etiketi(bas, bitis - timedelta(days=1)),
        target_note=rapor.hedef_notu(veri, bas, bitis),
        people=[PersonSummary(**k) for k in rapor.kisi_ozeti(veri, bas, bitis)],
        shortfalls=[Shortfall(**e) for e in rapor.eksikler(veri)],
    )
