"""E-02 Yetkinlik Matrisi · E-03 Kural Seti · E-01 Vardiya Tanımları."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from app.repositories import setup as repo
from app.schemas.setup import (
    Competency, CompetencyMatrix, Constraint, ConstraintParam, ConstraintUpdate,
    MatrixRow, ParamUpdate, ShiftType,
)

router = APIRouter(tags=["kurulum"])

KAPSAM_ADI = {
    "kisi": "Kişi", "vardiya": "Vardiya", "gun": "Gün", "hafta": "Hafta", "ay": "Ay",
}
KAYNAK_ADI = {
    "yasal": "Yasal", "kurumsal": "Kurumsal", "tercih": "Tercih", "belirsiz": "Belirsiz",
}


def _yetkinlik(c: dict) -> Competency:
    return Competency(
        id=c["id"], code=c["code"], name=c["name"], kind=c["kind"],
        description=c["description"], staff_count=c["staff_count"],
    )


@router.get("/competencies", response_model=list[Competency], summary="Yetkinlik listesi")
async def yetkinlikler() -> list[Competency]:
    return [_yetkinlik(c) for c in await repo.yetkinlikler()]


@router.get("/competency-matrix", response_model=CompetencyMatrix, summary="E-02 matrisi")
async def matris() -> CompetencyMatrix:
    hepsi = [_yetkinlik(c) for c in await repo.yetkinlikler()]
    return CompetencyMatrix(
        # Görev yetkinlikleri ayrı grupta: bunlar vardiya içinde ATANIR,
        # diğerleri kişinin taşıdığı yetkidir (migration 010).
        tasks=[c for c in hepsi if c.kind == "TASK"],
        qualifications=[c for c in hepsi if c.kind == "QUALIFICATION"],
        rows=[
            MatrixRow(
                staff_id=r["staff_id"], full_name=r["full_name"], role_name=r["role_name"],
                is_orientation=r["is_orientation"], codes=list(r["codes"] or []),
            )
            for r in await repo.matris()
        ],
    )


@router.put("/people/{staff_id}/competencies/{code}", response_model=CompetencyMatrix,
            summary="Yetkinlik kutucuğunu aç/kapa")
async def yetkinlik_degistir(staff_id: int, code: str, ver: bool) -> CompetencyMatrix:
    await repo.yetkinlik_degistir(staff_id, code, ver)
    return await matris()


def _kural(c: dict) -> Constraint:
    return Constraint(
        id=c["id"], code=c["code"], catalog_code=c["catalog_code"], name=c["name"],
        description=c["description"], is_hard=c["is_hard"],
        default_weight=c["default_weight"], scope=c["scope"],
        scope_label=KAPSAM_ADI.get(c["scope"], c["scope"]),
        source=c["source"], source_label=KAYNAK_ADI.get(c["source"], c["source"]),
        # Kaynağı "yasal" olan kural gevşetilemez (docs/kisit-katalogu.md)
        locked=c["source"] == "yasal",
        params=[ConstraintParam(**p) for p in (c["params"] or [])],
    )


@router.get("/constraints", response_model=list[Constraint], summary="Kural seti")
async def kurallar() -> list[Constraint]:
    return [_kural(c) for c in await repo.kurallar()]


@router.patch("/constraints/{constraint_id}", response_model=Constraint, summary="Kuralı düzenle")
async def kural_guncelle(constraint_id: int, istek: ConstraintUpdate) -> Constraint:
    mevcut = next((c for c in await repo.kurallar() if c["id"] == constraint_id), None)
    if mevcut is None:
        raise HTTPException(status_code=404, detail="Kural bulunamadı.")
    if mevcut["source"] == "yasal":
        raise HTTPException(status_code=403, detail="Yasal kurallar gevşetilemez.")

    alanlar = istek.model_dump(exclude_unset=True)
    # Veritabanı kuralı: hard → ağırlık NULL, soft → ağırlık > 0 (migration 003).
    # İkisini birlikte göndermek zorunda değil; eksik olanı burada tamamlıyoruz.
    hedef_hard = alanlar.get("is_hard", mevcut["is_hard"])
    if hedef_hard:
        alanlar["default_weight"] = None
    elif alanlar.get("default_weight") is None:
        alanlar["default_weight"] = mevcut["default_weight"] or 50
    alanlar["is_hard"] = hedef_hard

    try:
        await repo.kural_guncelle(constraint_id, alanlar)
    except Exception as hata:  # noqa: BLE001
        if "ck_constraints_weight_by_type" in str(hata):
            raise HTTPException(
                status_code=422,
                detail="Zorunlu kuralın ağırlığı olmaz; esnek kuralın ağırlığı pozitif olmalı.",
            ) from hata
        raise HTTPException(status_code=422, detail="Kural güncellenemedi.") from hata

    return _kural(next(c for c in await repo.kurallar() if c["id"] == constraint_id))


@router.patch("/constraint-params/{param_id}", response_model=list[Constraint],
              summary="Kural parametresini düzenle")
async def param_guncelle(param_id: int, istek: ParamUpdate) -> list[Constraint]:
    if await repo.param_guncelle(param_id, istek.param_value) is None:
        raise HTTPException(status_code=404, detail="Parametre bulunamadı.")
    return await kurallar()


@router.get("/shift-types", response_model=list[ShiftType], summary="Vardiya tanımları")
async def vardiyalar() -> list[ShiftType]:
    sonuc = []
    for v in await repo.vardiyalar():
        sure = float(v["duration_hours"])
        bitis = (datetime.combine(datetime.today(), v["start_time"])
                 + timedelta(hours=sure)).time()
        sonuc.append(ShiftType(
            id=v["id"], code=v["code"], name=v["name"], start_time=v["start_time"],
            duration_hours=sure, end_label=bitis.strftime("%H:%M"),
            crosses_midnight=v["crosses_midnight"], is_active=v["is_active"],
            unit_name=v["unit_name"],
        ))
    return sonuc
