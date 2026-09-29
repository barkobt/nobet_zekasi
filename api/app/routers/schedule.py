"""E-09 Nöbet Çizelgesi. Ham satırları ekranın istediği biçime çevirir."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query

from app.hedef import donem_hedefi, donem_turu, hedef_etiketi, izin_dusumu
from app.repositories import schedule as repo
from app.schemas.schedule import (
    Cell, CellRequest, CellResult, CellUpdate, CounterView, DayHeader, DraftInfo,
    Group, QualificationFlag, Row, Schedule, ShiftHeader, SlotCoverage, Summary,
)

router = APIRouter(prefix="/drafts", tags=["çizelge"])

GUN_ADI = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
AY_ADI = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

# Vardiya kodu → hücre çipi. DESIGN §6: yalnız G ve N, saat aralığı yazılmaz.
VARDIYA_ETIKET = {"GUNDUZ": "G", "GUNDUZ_CMT": "G", "GECE": "N"}

# Tooltip iki gruba ayrılıyor (26.09 kararı):
#   SAYILABILIR → "Triyaj 2/3 · 1 eksik" biçiminde, eksikse kırmızı
#   VAR_YOK     → "Ekip lideri ✓" biçiminde, sayı gösterilmez
# Sıra kasıtlı: triyaj → gözlem → ambulans. Alfabetik değil, işleyiş sırası.
SLOT_SIRA = ["TRIYAJ", "GOZLEM", "AMBULANS"]
SLOT_ADI = {"TRIYAJ": "Triyaj", "GOZLEM": "Gözlem", "AMBULANS": "Ambulans"}
YETKI_ADI = {"SHIFT_YETKILISI": "Ekip lideri", "SAYIM": "Sayım yetkilisi"}

# DESIGN §6: rol grubuna göre katlanabilir bölümler.
GRUPLAR = [
    ("sorumlu_egitim", "Sorumlu & Eğitim", {"sorumlu_hemsire", "egitim_hemsire"}),
    ("ekip_liderleri", "Ekip Liderleri", {"shift_yetkilisi"}),
    ("hemsireler", "Hemşireler", None),  # None = geri kalan herkes
]


def _bas_harfler(ad: str) -> str:
    parcalar = [p for p in ad.split() if p]
    return "".join(p[0].upper() for p in parcalar[:2])


def gun_basliklari(kapsama_satirlari: list[dict], gun_bas: date, gun_son: date,
                   donem: object | None = None) -> list[DayHeader]:
    """Kapsama satırlarını gün sütunlarına çevirir.

    Hem E-09 çizelgesi hem E-06 ihtiyaç ekranı bunu kullanır: aynı sayılar,
    aynı tooltip kuralları. İki yerde yazılsaydı zamanla birbirinden ayrılırdı.
    """
    kapsama: dict[tuple[date, str], list[dict]] = {}
    for k in kapsama_satirlari:
        kapsama.setdefault((k["day"], k["shift_code"]), []).append(k)

    gunler: list[DayHeader] = []
    gun = gun_bas
    while gun <= gun_son:
        vardiyalar: list[ShiftHeader] = []
        for kod in ("GUNDUZ", "GECE"):          # okuma sırası: önce gündüz
            satirlar = kapsama.get((gun, kod))
            if not satirlar:
                continue
            genel = next((s for s in satirlar if s["slot_code"] == "GENEL"), None)

            # Ambulans çıkınca boşalan alan var mı? Tooltip'in tek açıklama satırı.
            bos_alan = next(
                (SLOT_ADI[s["slot_code"]].lower()
                 for s in satirlar
                 if s["slot_code"] in ("TRIYAJ", "GOZLEM") and s["remaining_after_ambulance"] == 0),
                None,
            )

            vardiyalar.append(
                ShiftHeader(
                    code=kod,
                    label=VARDIYA_ETIKET.get(kod, "G"),
                    assigned=genel["assigned"] if genel else 0,
                    required=genel["required"] if genel else 0,
                    slots=[
                        SlotCoverage(
                            slot_code=s["slot_code"], label=SLOT_ADI[s["slot_code"]],
                            assigned=s["assigned"], required=s["required"],
                        )
                        for s in sorted(
                            (x for x in satirlar if x["slot_code"] in SLOT_ADI),
                            key=lambda x: SLOT_SIRA.index(x["slot_code"]),
                        )
                    ],
                    flags=[
                        QualificationFlag(
                            label=YETKI_ADI[s["slot_code"]],
                            present=s["assigned"] >= s["required"],
                        )
                        for s in sorted(
                            (x for x in satirlar if x["slot_code"] in YETKI_ADI),
                            key=lambda x: x["slot_code"], reverse=True,
                        )
                    ],
                    empty_area=bos_alan,
                )
            )
        gunler.append(
            DayHeader(
                day=gun,
                weekday=GUN_ADI[gun.weekday()],
                label=f"{gun.day} {AY_ADI[gun.month - 1]}",
                is_weekend=gun.weekday() >= 5,
                # donem verilmezse (E-06 ihtiyaç ekranı) her gün dönem içi sayılır.
                in_period=donem is None or donem.lower <= gun < donem.upper,
                shifts=vardiyalar,
            )
        )
        gun += timedelta(days=1)
    return gunler


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

    # Dönem dışı günlerin başlığı yayınlanmış çizelgenin kapsamasından gelir:
    # 26 Eki–1 Kas haftasında 26-31 Ekim'in G 6/6'sı Ekim çizelgesinden okunur.
    gunler = gun_basliklari(
        veri["kapsama"] + veri["dis_kapsama"], gun_bas, gun_son, veri["donem"]
    )
    aralik_gunleri = [gun_bas + timedelta(days=i) for i in range((gun_son - gun_bas).days + 1)]

    # Görünen aralık haftalık mı aylık mı: sayaç görünürlüğü ikisi için ayrı ayarlanıyor.
    # Ölçüt aralığın UZUNLUĞU: bir hafta 7 gün, ay görünümü 28-31 gün. 14 gün eşiği
    # ikisinin arasında güvenli bir sınır.
    gorunum = "monthly" if len(aralik_gunleri) > 14 else "weekly"
    sayac_gorunurluk = [
        CounterView(
            key=c["key"], badge=c["badge"], label=c["label"],
            always_shown=c["always_shown"],
            visible=c["always_shown"] or (c["monthly_on"] if gorunum == "monthly"
                                         else c["weekly_on"]),
        )
        for c in veri["sayaclar"]
    ]

    # --- Hücreler -----------------------------------------------------------
    donem = veri["donem"]
    # Hücrede gösterilen saat de NET (mola hariç, 023). Brüt bırakılsaydı satır
    # sonundaki "S" sayacı hücrelerin toplamını tutmazdı: 21 hücre × 9,5 ≠ 205,5.
    sureler = {k: round(int(v["net_minutes"]) / 60.0, 2) for k, v in veri["vardiyalar"].items()}

    hucreler: dict[int, dict[str, Cell]] = {}
    # Dönem dışı satırlar ÖNCE yazılır ki taslağın kendi satırı (varsa) üstüne yazsın.
    for a in veri["dis_atamalar"] + veri["atamalar"]:
        g = a["work_date"]
        icinde = donem.lower <= g < donem.upper
        hucreler.setdefault(a["staff_id"], {})[g.isoformat()] = Cell(
            shift_code=a["shift_code"],
            shift_label=VARDIYA_ETIKET.get(a["shift_code"], "G"),
            tasks=list(a["tasks"] or []),
            is_locked=a["is_locked"],
            source=a["source"],
            hours=sureler.get(a["shift_code"], 0.0),
            editable=icinde,
        )

    # --- Hücredeki istek işaretleri -----------------------------------------
    ISTEK_ADI = {"BOS_GUN": "Boş gün", "SADECE_GUNDUZ": "Sadece gündüz",
                 "SADECE_GECE": "Sadece gece"}
    GUC_ADI = {"KESIN": "Kesin", "MUMKUNSE": "Mümkünse"}
    istek_hucreleri: dict[int, dict[str, CellRequest]] = {}
    for i in veri["hucre_istekleri"]:
        tur = i["rule_type"]
        if tur not in ISTEK_ADI:
            continue                     # eski türler (off_talebi vb.) ekranda gösterilmez
        iso = i["target_date"].isoformat()
        h = hucreler.get(i["staff_id"], {}).get(iso)
        istek_hucreleri.setdefault(i["staff_id"], {})[iso] = CellRequest(
            type=tur,
            type_label=ISTEK_ADI[tur],
            strength=i["status"],
            strength_label=GUC_ADI.get(i["status"], i["status"]),
            met=repo.istek_karsilandi(
                tur,
                {"shift_code": h.shift_code} if h else None,
                veri["vardiyalar"],
            ),
            note=i["note"],
        )

    izinler: dict[int, dict[str, str]] = {}
    for iz in veri["izinler"]:
        g = max(iz["period"].lower, gun_bas)
        son = min(iz["period"].upper - timedelta(days=1), gun_son)
        while g <= son:
            izinler.setdefault(iz["staff_id"], {})[g.isoformat()] = iz["absence_type"]
            g += timedelta(days=1)

    aylik = {m["staff_id"]: m for m in veri["aylik"]}

    # Hedef saat: orantı YOK (bkz. app/hedef.py). Tam ay → 200, tam hafta → 50,
    # başka uzunlukta hedef gösterilmez.
    tur = donem_turu(bas, bitis)
    haftalik_ref = veri["hedefler"].get("weekly_reference_hours")
    gunluk_dusum = veri["hedefler"].get("absence_daily_reduction_hours")
    izin_gunleri = veri["izin_gunleri"]

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
            planlanan = float(m["net_hours"]) if m else 0.0   # NET (mola hariç, 023)
            # Aylık hedeften izin günleri düşülür — solver de aynısını yapıyor.
            hedef = izin_dusumu(
                donem_hedefi(
                    tur, float(m["min_hours"]) if m and m["min_hours"] else None, haftalik_ref
                ),
                izin_gunleri.get(k["id"], 0) if tur == "ay" else 0,
                gunluk_dusum,
            )
            # Sayaçlar GÖRÜNEN ARALIĞI ölçer (satır sonundaki period_hours ise taslağın
            # tamamını). Haftalık görünümde "S" o haftanın saati, aylıkta ayın saati.
            gorunen_tur = donem_turu(gun_bas, gun_son + timedelta(days=1))
            gorunen_hedef = izin_dusumu(
                donem_hedefi(
                    gorunen_tur,
                    float(m["min_hours"]) if m and m["min_hours"] else None,
                    haftalik_ref,
                ),
                izin_gunleri.get(k["id"], 0) if gorunen_tur == "ay" else 0,
                gunluk_dusum,
            )
            sayaclar = repo.sayac_degerleri(
                staff_id=k["id"],
                hucreler={iso: {"shift_code": c.shift_code, "tasks": c.tasks}
                          for iso, c in hucreler.get(k["id"], {}).items()},
                gunler=aralik_gunleri,
                vardiyalar=veri["vardiyalar"],
                istekler=veri["istekler"],
                hedef=gorunen_hedef,
            )
            satirlar.append(
                Row(
                    staff_id=k["id"],
                    full_name=k["full_name"],
                    role_name=k["role_name"],
                    is_orientation=k["is_orientation"],
                    is_active=k["is_active"],
                    in_fairness=k["adalete_girer"],
                    initials=_bas_harfler(k["full_name"]),
                    cells=hucreler.get(k["id"], {}),
                    absences=izinler.get(k["id"], {}),
                    requests=istek_hucreleri.get(k["id"], {}),
                    period_hours=planlanan,
                    period_target=hedef,
                    period_diff=round(planlanan - hedef, 1) if hedef is not None else None,
                    shift_count=int(m["shift_count"]) if m else 0,
                    counters=sayaclar,
                )
            )
        if satirlar:
            gruplar.append(Group(key=anahtar, label=etiket, rows=satirlar))

    # --- Alt bar ------------------------------------------------------------
    # Alt bar GÖRÜNEN dönemi özetler (kullanıcının baktığı hafta ya da ay), o yüzden
    # satır sayaçlarından toplanır — period_hours taslağın tamamını ölçüyor.
    tum_satirlar = [r for g in gruplar for r in g.rows]
    gorunen_saat = round(sum(r.counters.get("S") or 0 for r in tum_satirlar), 1)
    gorunen_gece = int(sum(r.counters.get("N") or 0 for r in tum_satirlar))
    toplam_saat = round(sum(r.period_hours for g in gruplar for r in g.rows), 1)
    fazla_mesai = round(sum(float(m["overtime_max"]) for m in veri["aylik"]), 1)
    # Adalet farkı YALNIZ adalet havuzundan. Oryantasyon eşini gölgelediği için
    # saati yüksek, sorumlunun programı sabit; onları katmak farkı yanlış büyütür
    # ve ekran solver'ın raporladığı rakamla çelişirdi.
    calisan_saatler = [s for r in tum_satirlar
                       if r.in_fairness and (s := r.counters.get("S") or 0) > 0]
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
            target_label=hedef_etiketi(
                tur,
                donem_hedefi(
                    tur,
                    next((float(m["min_hours"]) for m in veri["aylik"] if m["min_hours"]), None),
                    haftalik_ref,
                ),
            ),
        ),
        days=gunler,
        groups=gruplar,
        summary=Summary(
            total_hours=gorunen_saat,
            overtime_hours=fazla_mesai,
            fairness_gap=adalet,
            shortfall_count=eksik,
            total_nights=gorunen_gece,
        ),
        view=gorunum,
        counters=sayac_gorunurluk,
        notes=notlar,
    )


@router.put("/{draft_id}/cells", response_model=CellResult, summary="Hücreye elle müdahale")
async def hucre_yaz(draft_id: int, istek: CellUpdate) -> CellResult:
    """Elle yazılan hücre source='manuel', is_locked=TRUE olur: solver dokunmaz.

    Kural uyarıları ENGELLEMEZ. Sorumlu hemşire gerçekliği bildiğinde çizelgeye
    yazabilmeli; sistem yalnız neyin ihlal edildiğini söyler (E-09 kararı).
    """
    if await repo.taslak(draft_id) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")

    yazildi, uyarilar = await repo.hucre_yaz(
        draft_id, istek.staff_id, istek.work_date, istek.shift_code, istek.tasks
    )
    # ok=False → hiçbir şey yazılmadı. Arayüz "kaydedildi" demesin.
    return CellResult(ok=yazildi, warnings=uyarilar)
