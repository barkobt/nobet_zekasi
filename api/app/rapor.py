"""Rapor hesapları — TEK yer.

Kişi özeti ve eksikler listesi üç yerde görünüyor: Raporlar ekranı, o ekranın
Excel düğmeleri ve (eskiden) çizelge Excel'inin sayfaları. Hesap üç yere
kopyalanırsa zamanla birbirinden ayrılır; bu yüzden hepsi buradan okur.

Kaynak veri `repositories/schedule.cizelge_verisi` — ekranın gördüğü satırların
aynısı, ayrıca sorgu yok.
"""

from datetime import date

from app.hedef import donem_hedefi, donem_turu, hedef_etiketi

VARDIYA_ADI = {"GUNDUZ": "Gündüz", "GECE": "Gece", "GUNDUZ_CMT": "Gündüz (Cmt)"}
SLOT_ADI = {
    "GENEL": "Genel mevcut", "TRIYAJ": "Triyaj", "GOZLEM": "Gözlem",
    "AMBULANS": "Ambulans", "SAYIM": "Sayım yetkilisi", "SHIFT_YETKILISI": "Ekip lideri",
}


def haftalik_mesai(veri: dict) -> dict[int, dict]:
    """Kişi başına fazla mesai: haftalık BRÜT 51 saatin üstü (O-001).

    Maaş hesabı böyle (Edem, 30.09): molalar dahil haftalık 51 saat ücret bazı,
    üstündeki her saat mesai. Aylık mesai = haftalık fazlaların toplamı; hafta
    Pazar gününün düştüğü aya yazılır (sorgu: repositories/schedule._HAFTALIK_BRUT).
    Sınır koda gömülü değil: constraint_params.weekly_paid_gross_hours.
    """
    sinir = veri["hedefler"].get("weekly_paid_gross_hours")
    sonuc: dict[int, dict] = {}
    for r in veri.get("haftalik_brut", []):
        k = sonuc.setdefault(r["staff_id"], {"brut_dk": 0, "mesai_dk": 0, "hafta": 0})
        k["brut_dk"] += r["brut_dk"]
        k["hafta"] += 1
        if sinir:
            k["mesai_dk"] += max(0, r["brut_dk"] - int(sinir * 60))
    return sonuc


def kisi_ozeti(veri: dict, bas: date, bitis_dis: date) -> list[dict]:
    """Personel × (toplam saat · gece · hafta sonu · hedef · fark · mesai)."""
    tur = donem_turu(bas, bitis_dis)
    mesai = haftalik_mesai(veri)
    haftalik = veri["hedefler"].get("weekly_min_net_hours")

    aylik = {m["staff_id"]: m for m in veri["aylik"]}
    gece: dict[int, int] = {}
    haftasonu: dict[int, int] = {}
    for a in veri["atamalar"]:
        if a["crosses_midnight"]:
            gece[a["staff_id"]] = gece.get(a["staff_id"], 0) + 1
        if a["work_date"].weekday() >= 5:
            haftasonu[a["staff_id"]] = haftasonu.get(a["staff_id"], 0) + 1

    satirlar = []
    for k in veri["personel"]:
        m = aylik.get(k["id"])
        # NET saat (mola hariç, migration 023). Hedef de net olduğu için ikisi
        # aynı dilde: "200 sa" karşılaştırması brütle anlamsız olurdu.
        saat = float(m["net_hours"]) if m else 0.0
        # Aylık hedef kişiye göre değişebiliyor (v_monthly_hours.min_hours);
        # haftalıkta böyle bir kişiselleştirme yok, tek referans değer.
        hedef = donem_hedefi(tur, float(m["min_hours"]) if m and m["min_hours"] else None, haftalik)
        satirlar.append({
            "staff_id": k["id"],
            "full_name": k["full_name"],
            "role_name": k["role_name"],
            "total_hours": round(saat, 1),
            "night_count": gece.get(k["id"], 0),
            "weekend_count": haftasonu.get(k["id"], 0),
            "target_hours": hedef,
            "diff_hours": round(saat - hedef, 1) if hedef is not None else None,
            # Brüt, net ile AYNI dönemden (v_monthly_hours); mesai ise haftalık
            # hesaplanıp Pazar'ın düştüğü aya yazılır — iki sütunun kapsamı farklı.
            "gross_hours": round(float(m["gross_hours"]), 1) if m else 0.0,
            "overtime_hours": round(mesai.get(k["id"], {}).get("mesai_dk", 0) / 60.0, 1),
        })
    return satirlar


def eksikler(veri: dict) -> list[dict]:
    """Kapsama satırlarından yalnız eksik olanlar, gün → vardiya → slot sırasıyla."""
    return [
        {
            "day": k["day"],
            "shift_code": k["shift_code"],
            "shift_name": VARDIYA_ADI.get(k["shift_code"], k["shift_code"]),
            "slot_code": k["slot_code"],
            "slot_name": SLOT_ADI.get(k["slot_code"], k["slot_code"]),
            "assigned": k["assigned"],
            "required": k["required"],
            "missing": k["required"] - k["assigned"],
        }
        for k in sorted(veri["kapsama"], key=lambda x: (x["day"], x["shift_code"], x["slot_code"]))
        if k["assigned"] < k["required"]
    ]


def hedef_notu(veri: dict, bas: date, bitis_dis: date) -> str | None:
    tur = donem_turu(bas, bitis_dis)
    ilk = next((m for m in veri["aylik"] if m["min_hours"]), None)
    hedef = donem_hedefi(
        tur,
        float(ilk["min_hours"]) if ilk else None,
        veri["hedefler"].get("weekly_min_net_hours"),
    )
    return hedef_etiketi(tur, hedef)
