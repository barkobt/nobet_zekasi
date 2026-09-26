"""E-09 Nöbet Çizelgesi. Ham satırları ekranın istediği biçime çevirir."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.repositories import schedule as repo
from app.schemas.schedule import (
    Cell, DayHeader, DraftInfo, Group, Row, Schedule, ShiftHeader, SlotCoverage, Summary,
)

router = APIRouter(prefix="/drafts", tags=["çizelge"])

GUN_ADI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AY_ADI = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

# Vardiya kodu → hücre çipi. DESIGN §6: yalnız G ve N, saat aralığı yazılmaz.
VARDIYA_ETIKET = {"GUNDUZ": "G", "GUNDUZ_CMT": "G", "GECE": "N"}

SLOT_ADI = {
    "GENEL": "Genel mevcut",
    "TRIYAJ": "Triyaj",
    "AMBULANS": "Ambulans",
    "GOZLEM": "Gözlem",
    "SAYIM": "Sayım yetkilisi",
    "SHIFT_YETKILISI": "Ekip lideri",
}

# DESIGN §6: rol grubuna göre katlanabilir bölümler.
GRUPLAR = [
    ("sorumlu_egitim", "Sorumlu & Eğitim", {"sorumlu_hemsire", "egitim_hemsire"}),
    ("ekip_liderleri", "Ekip Liderleri", {"shift_yetkilisi"}),
    ("hemsireler", "Hemşireler", None),  # None = geri kalan herkes
]


def _bas_harfler(ad: str) -> str:
    parcalar = [p for p in ad.split() if p]
    return "".join(p[0].upper() for p in parcalar[:2])


@router.get("/{draft_id}/schedule", response_model=Schedule, summary="E-09 çizelge ızgarası")
async def cizelge(
    draft_id: int,
    gun_bas: date = Query(alias="from", description="Aralık başlangıcı (dahil)"),
    gun_son: date = Query(alias="to", description="Aralık bitişi (dahil)"),
) -> Schedule:
    if gun_son < gun_bas:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan önce olamaz.")
    if (gun_son - gun_bas).days > 45:
        raise HTTPException(status_code=422, detail="Aralık en fazla 45 gün olabilir.")

    if (t := await repo.taslak(draft_id)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")

    # Aylık hedef (C-004) karşılaştırması iki koşul ister:
    #   1) taslağın aralığı TAM bir takvim ayı olmalı
    #   2) atamalar o aralığı baştan sona kapsamalı
    # İkisinden biri yoksa "200 saatin altında" demek anlamsız.
    bas, bitis = t["period_start"], t["period_end"]   # bitis DIŞLAYICI
    sonraki_ay = date(bas.year + (bas.month == 12), bas.month % 12 + 1, 1)
    tam_takvim_ayi = bas.day == 1 and bitis == sonraki_ay
    tam_ay = bool(
        tam_takvim_ayi
        and t["ilk_gun"] and t["son_gun"]
        and t["ilk_gun"] <= bas and t["son_gun"] >= bitis - timedelta(days=1)
    )

    veri = await repo.cizelge_verisi(draft_id, gun_bas, gun_son)

    # --- Sütun başlıkları ---------------------------------------------------
    # kapsama satırlarını (gün, vardiya) altında topla
    kapsama: dict[tuple[date, str], list[dict]] = {}
    for k in veri["kapsama"]:
        kapsama.setdefault((k["day"], k["shift_code"]), []).append(k)

    gunler: list[DayHeader] = []
    gun = gun_bas
    while gun <= gun_son:
        vardiyalar: list[ShiftHeader] = []
        # GUNDUZ önce, GECE sonra — okuma sırası
        for kod in ("GUNDUZ", "GECE"):
            satirlar = kapsama.get((gun, kod))
            if not satirlar:
                continue
            genel = next((s for s in satirlar if s["slot_code"] == "GENEL"), None)
            vardiyalar.append(
                ShiftHeader(
                    code=kod,
                    label=VARDIYA_ETIKET.get(kod, "G"),
                    # Başlık sayacı YALNIZCA genel mevcut (DESIGN §6)
                    assigned=genel["assigned"] if genel else 0,
                    required=genel["required"] if genel else 0,
                    slots=[
                        SlotCoverage(
                            slot_code=s["slot_code"],
                            label=SLOT_ADI.get(s["slot_code"], s["slot_code"]),
                            assigned=s["assigned"],
                            required=s["required"],
                            qualified=s["qualified"],
                            remaining_after_ambulance=s["remaining_after_ambulance"],
                        )
                        for s in satirlar
                        if s["slot_code"] != "GENEL"
                    ],
                )
            )
        gunler.append(
            DayHeader(
                day=gun,
                weekday=GUN_ADI[gun.weekday()],
                label=f"{gun.day} {AY_ADI[gun.month - 1]}",
                is_weekend=gun.weekday() >= 5,
                shifts=vardiyalar,
            )
        )
        gun += timedelta(days=1)

    # --- Hücreler -----------------------------------------------------------
    hucreler: dict[int, dict[str, Cell]] = {}
    for a in veri["atamalar"]:
        hucreler.setdefault(a["staff_id"], {})[a["work_date"].isoformat()] = Cell(
            shift_code=a["shift_code"],
            shift_label=VARDIYA_ETIKET.get(a["shift_code"], "G"),
            tasks=list(a["tasks"] or []),
            is_locked=a["is_locked"],
            source=a["source"],
        )

    izinler: dict[int, dict[str, str]] = {}
    for iz in veri["izinler"]:
        g = max(iz["period"].lower, gun_bas)
        son = min(iz["period"].upper - timedelta(days=1), gun_son)
        while g <= son:
            izinler.setdefault(iz["staff_id"], {})[g.isoformat()] = iz["absence_type"]
            g += timedelta(days=1)

    aylik = {m["staff_id"]: m for m in veri["aylik"]}

    # --- Satırlar, rol grubuna göre -----------------------------------------
    gruplar: list[Group] = []
    for anahtar, etiket, roller in GRUPLAR:
        satirlar: list[Row] = []
        for k in veri["personel"]:
            if roller is None:
                if any(k["role_code"] in r for _, _, r in GRUPLAR if r):
                    continue
            elif k["role_code"] not in roller:
                continue

            m = aylik.get(k["id"])
            planlanan = float(m["planned_hours"]) if m else 0.0
            hedef = float(m["min_hours"]) if m else 0.0
            satirlar.append(
                Row(
                    staff_id=k["id"],
                    full_name=k["full_name"],
                    role_name=k["role_name"],
                    is_orientation=k["is_orientation"],
                    initials=_bas_harfler(k["full_name"]),
                    cells=hucreler.get(k["id"], {}),
                    absences=izinler.get(k["id"], {}),
                    month_hours=planlanan,
                    month_target=hedef,
                    month_diff=round(planlanan - hedef, 1),
                    shift_count=int(m["shift_count"]) if m else 0,
                )
            )
        if satirlar:
            gruplar.append(Group(key=anahtar, label=etiket, rows=satirlar))

    # --- Alt bar ------------------------------------------------------------
    toplam_saat = round(sum(r.month_hours for g in gruplar for r in g.rows), 1)
    fazla_mesai = round(sum(float(m["overtime_max"]) for m in veri["aylik"]), 1)
    calisan_saatler = [r.month_hours for g in gruplar for r in g.rows if r.month_hours > 0]
    adalet = round(max(calisan_saatler) - min(calisan_saatler), 1) if calisan_saatler else 0.0
    eksik = sum(1 for k in veri["kapsama"] if k["assigned"] < k["required"])

    # --- Izgara altı notlar -------------------------------------------------
    notlar: list[str] = []
    # Triyaj rozetleri artık seeds/011 ile kuraldan türetiliyor; "kağıtta kayıtlı değil"
    # notu kalktı. Yerine ambulans sonrası alan boşalması uyarısı var (C-009).
    bos_alan = sum(
        1 for k in veri["kapsama"]
        if k["remaining_after_ambulance"] == 0 and k["slot_code"] in ("TRIYAJ", "GOZLEM")
    )
    if bos_alan:
        notlar.append(
            f"{bos_alan} vardiyada ambulans çıktığında triyaj veya gözlem alanında "
            "kimse kalmıyor (C-009)."
        )
    if not tam_ay and t["ilk_gun"]:
        notlar.append(
            f"Bu taslak yalnızca {t['ilk_gun'].strftime('%d.%m')}–{t['son_gun'].strftime('%d.%m')} "
            "aralığını içerir; ay toplamları bu aralığa aittir."
        )

    return Schedule(
        draft=DraftInfo(
            id=t["id"], name=t["name"],
            period_start=t["period_start"], period_end=t["period_end"],
            status=t["status"], unit_name=t["unit_name"], covers_full_month=tam_ay,
        ),
        days=gunler,
        groups=gruplar,
        summary=Summary(
            total_hours=toplam_saat,
            overtime_hours=fazla_mesai,
            fairness_gap=adalet,
            shortfall_count=eksik,
        ),
        notes=notlar,
    )
