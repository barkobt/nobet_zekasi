"""E-06 İhtiyaç — haftalık görünüm + düzenlenebilir şablon."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.repositories import demand as repo
from app.repositories import overview as overview_repo
from app.repositories import schedule as schedule_repo
from app.routers.overview import _etiket
from app.routers.schedule import gun_basliklari
from app.schemas.demand import (
    Demand, DemandDraft, DemandTotal, NeedTemplate, TemplateRow, TemplateRowCreate,
    TemplateRowUpdate,
)

router = APIRouter(tags=["ihtiyaç"])

SLOT_ETIKET = {
    "GENEL": "Genel mevcut",
    "TRIYAJ": "Triyaj",
    "GOZLEM": "Gözlem",
    "AMBULANS": "Ambulans",
    "SAYIM": "Sayım yetkilisi",
    "SHIFT_YETKILISI": "Ekip lideri",
}


@router.get("/demand", response_model=Demand, summary="Haftalık ihtiyaç görünümü")
async def haftalik(
    gun_bas: date = Query(alias="from"),
    gun_son: date = Query(alias="to", description="DAHİL"),
) -> Demand:
    if gun_son < gun_bas:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan önce olamaz.")
    if (gun_son - gun_bas).days > 45:
        raise HTTPException(status_code=422, detail="Aralık en fazla 45 gün olabilir.")

    bitis = gun_son + timedelta(days=1)
    gereken = await repo.gereken_saat(gun_bas, bitis)
    ozet = await overview_repo.ozet(gun_bas, bitis)
    t = ozet["taslak"]

    if t is None:
        return Demand(
            period_label=_etiket(gun_bas, bitis),
            period_start=gun_bas, period_end=bitis, draft=None,
            total=DemandTotal(required_hours=round(gereken, 1), assigned_hours=0, shortfall_count=0),
            days=[],
        )

    veri = await schedule_repo.cizelge_verisi(t["id"], gun_bas, gun_son)
    gunler = gun_basliklari(veri["kapsama"], gun_bas, gun_son)
    eksik = sum(1 for k in veri["kapsama"] if k["assigned"] < k["required"])

    return Demand(
        period_label=_etiket(gun_bas, bitis),
        period_start=gun_bas,
        period_end=bitis,
        draft=DemandDraft(
            id=t["id"], name=t["name"],
            is_published=t["status"] == "yayinlandi",
            is_reference_copy=t["solver_impl"] == "stub",
        ),
        total=DemandTotal(
            required_hours=round(gereken, 1),
            assigned_hours=round(ozet["atanan"], 1),
            shortfall_count=eksik,
        ),
        days=gunler,
    )


@router.get("/need-templates", response_model=list[NeedTemplate], summary="İhtiyaç şablonu")
async def sablon() -> list[NeedTemplate]:
    satirlar = await repo.sablon()
    sablonlar: dict[int, NeedTemplate] = {}
    for s in satirlar:
        nt = sablonlar.setdefault(
            s["template_id"],
            NeedTemplate(id=s["template_id"], code=s["template_code"],
                         name=s["template_name"], rows=[]),
        )
        nt.rows.append(TemplateRow(
            id=s["id"], shift_code=s["shift_code"], shift_name=s["shift_name"],
            slot_code=s["slot_code"], slot_label=SLOT_ETIKET.get(s["slot_code"], s["slot_code"]),
            min_count=s["min_count"], competency_codes=list(s["competency_codes"] or []),
            constraint_code=s["constraint_code"], catalog_code=s["catalog_code"],
            constraint_name=s["constraint_name"], is_hard=s["is_hard"],
        ))
    return list(sablonlar.values())


@router.patch("/need-template-rows/{row_id}", response_model=TemplateRow,
              summary="Şablon satırının kişi sayısını değiştir")
async def satir_guncelle(row_id: int, istek: TemplateRowUpdate) -> TemplateRow:
    if await repo.satir_guncelle(row_id, istek.min_count) is None:
        raise HTTPException(status_code=404, detail="Şablon satırı bulunamadı.")
    # Güncel satırı tek kaynaktan oku: gösterilen değer yazılan değerle aynı olsun.
    for nt in await sablon():
        for r in nt.rows:
            if r.id == row_id:
                return r
    raise HTTPException(status_code=404, detail="Şablon satırı bulunamadı.")


@router.post("/need-templates/{template_id}/rows", response_model=list[NeedTemplate],
             status_code=201, summary="Şablona satır ekle")
async def satir_ekle(template_id: int, istek: TemplateRowCreate) -> list[NeedTemplate]:
    try:
        yeni = await repo.satir_ekle(
            template_id, istek.shift_code, istek.slot_code.upper(),
            istek.min_count, [c.upper() for c in istek.competency_codes],
        )
    except Exception as hata:  # noqa: BLE001
        if "uq_ntr_template_shift_slot" in str(hata):
            raise HTTPException(
                status_code=409, detail="Bu vardiyada aynı slot zaten tanımlı."
            ) from hata
        raise HTTPException(status_code=422, detail="Satır eklenemedi.") from hata
    if yeni is None:
        raise HTTPException(status_code=404, detail="Vardiya bulunamadı.")
    return await sablon()


@router.delete("/need-template-rows/{row_id}", response_model=list[NeedTemplate],
               summary="Şablon satırını sil")
async def satir_sil(row_id: int) -> list[NeedTemplate]:
    if await repo.satir_sil(row_id) is None:
        raise HTTPException(status_code=404, detail="Şablon satırı bulunamadı.")
    return await sablon()
