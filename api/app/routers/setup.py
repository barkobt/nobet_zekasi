"""E-02 Yetkinlik Matrisi · E-03 Kural Seti · E-01 Vardiya Tanımları."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from psycopg.errors import CheckViolation

from app.repositories import setup as repo
from app.schemas.setup import (
    BreakUpdate,
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
    # Eskiden yazım hatası olan bir kod 200 dönüp hiçbir şey yazmıyordu.
    if not await repo.personel_var_mi(staff_id):
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    if not await repo.yetkinlik_var_mi(code):
        raise HTTPException(status_code=404, detail=f"\"{code}\" diye bir yetkinlik yok.")
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
    hedef_hard = alanlar.get("is_hard", mevcut["is_hard"])
    if hedef_hard:
        alanlar["default_weight"] = None
    elif alanlar.get("default_weight") is None:
        if mevcut["default_weight"] is None:
            # Zorunlu kuralın ağırlığı yoktur; esneğe çevirirken UYDURMUYORUZ.
            # Eskiden sessizce 50 yazılıyordu ve iki tıkla ağırlık kayboluyordu.
            raise HTTPException(
                status_code=422,
                detail="Esnek kuralın ağırlığı olmalı. Ağırlığı da gönderin.",
            )
        alanlar["default_weight"] = mevcut["default_weight"]
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
    # Kuralın kendisi kilitliyse PARAMETRESİ de kilitli olmalı. Aksi halde
    # "haftada en az 1 dinlenme" kuralı 99'a çekilerek kilit anlamsızlaşıyordu.
    if (k := await repo.param_kurali(param_id)) is None:
        raise HTTPException(status_code=404, detail="Parametre bulunamadı.")
    if k["source"] == "yasal":
        raise HTTPException(
            status_code=403,
            detail=f"{k['name']} yasal bir kural; parametresi değiştirilemez.",
        )
    if await repo.param_guncelle(param_id, istek.param_value) is None:
        raise HTTPException(status_code=404, detail="Parametre bulunamadı.")
    return await kurallar()


def _net_etiket(dakika: int) -> str:
    """490 → '8 sa 10 dk', 660 → '11 sa'. Ondalık saat YAZILMAZ: gündüzün neti
    8,1666… eder ve "8,2 sa" ekranda yanlış bir kesinlik hissi verir."""
    sa, dk = divmod(dakika, 60)
    return f"{sa} sa {dk} dk" if dk else f"{sa} sa"


@router.get("/shift-types", response_model=list[ShiftType], summary="Vardiya tanımları")
async def vardiyalar() -> list[ShiftType]:
    sonuc = []
    for v in await repo.vardiyalar():
        sure = float(v["duration_hours"])
        # Bitiş saati BRÜT süreden hesaplanır: mola vardiyanın içinde geçer,
        # kişi yine de 18:00'de çıkar. Net yalnız mesai hesabına girer.
        bitis = (datetime.combine(datetime.today(), v["start_time"])
                 + timedelta(hours=sure)).time()
        sonuc.append(ShiftType(
            id=v["id"], code=v["code"], name=v["name"], start_time=v["start_time"],
            duration_hours=sure,
            break_minutes=v["break_minutes"], net_minutes=v["net_minutes"],
            net_label=_net_etiket(v["net_minutes"]),
            end_label=bitis.strftime("%H:%M"),
            crosses_midnight=v["crosses_midnight"], is_active=v["is_active"],
            unit_name=v["unit_name"],
        ))
    return sonuc


@router.put("/shift-types/{shift_type_id}/break", response_model=list[ShiftType],
            summary="Vardiya molasını kaydet")
async def mola_kaydet(shift_type_id: int, istek: BreakUpdate) -> list[ShiftType]:
    try:
        sonuc = await repo.mola_guncelle(shift_type_id, istek.break_minutes)
    except CheckViolation as hata:
        # ck_shift_types_break: mola vardiyadan kısa olmalı (migration 023).
        # Kural veritabanında; burada yalnız Türkçeye çevriliyor (CLAUDE.md).
        raise HTTPException(
            status_code=422,
            detail="Mola, vardiya süresinden kısa olmalı.",
        ) from hata
    if sonuc is None:
        raise HTTPException(status_code=404, detail="Vardiya bulunamadı.")
    return await vardiyalar()
