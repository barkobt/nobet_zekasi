"""Excel çıktıları.

Üç ayrı dosya, her biri TEK sayfa (27.09 kararı):
  * çizelge      → /drafts/{id}/export.xlsx
  * kişi özeti   → /drafts/{id}/export-ozet.xlsx      (Raporlar ekranı)
  * eksikler     → /drafts/{id}/export-eksikler.xlsx  (Raporlar ekranı)

Çizelge dosyasında eskiden Özet ve Eksikler sayfaları da vardı; onlar
Raporlar ekranına taşındı. Hesaplar app/rapor.py'de, tek yerde.
"""

from datetime import date, timedelta
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from openpyxl.cell.text import InlineFont
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

from app import rapor
from app.repositories import schedule as repo
from app.routers.schedule import AY_ADI, GUN_ADI, VARDIYA_ETIKET

router = APIRouter(tags=["çıktı"])

# DESIGN §2 renkleri — ekranla aynı dil
BRAND = "1D265F"
BEYAZ = "FFFFFF"
ZEMIN = "F5F7FA"
HAFTASONU = "EEF1F5"
CIZGI = "E3E8EF"
GRI = "5B6B7F"
KIRMIZI = "C62828"

GOREV_KISA = {"TRIYAJ": "TRY", "AMBULANS": "AMB", "GOZLEM": "GÖZ"}
IZIN_ADI = {"yillik_izin": "İzin", "rapor": "Rapor", "ucretsiz_izin": "İzin", "diger": "İzin"}
DURUM_ADI = {"taslak": "Taslak", "yayinlandi": "Yayında", "arsiv": "Arşiv"}

ince = Side(style="thin", color=CIZGI)
kalin = Side(style="medium", color=GRI)
KENARLIK = Border(left=ince, right=ince, top=ince, bottom=ince)
# Pazar'dan sonraki hafta ayracı: sağ kenarı kalın
HAFTA_SONU_KENARLIK = Border(left=ince, right=kalin, top=ince, bottom=ince)

ACIKLAMA = ("G = Gündüz 08:30–18:00 · N = Gece 18:00–08:30 · TRY = Triyaj · "
            "AMB = Ambulans · GÖZ = Gözlem · boş = çalışmıyor")

# Hücrenin iki satırı farklı biçimde: üstte vardiya harfi büyük+kalın, altta
# görevler küçük+soluk. Tek Font ile olmuyor, hücre içi zengin metin gerekiyor.
GUNDUZ_HARF = InlineFont(sz=11, b=True, color=BRAND)
GECE_HARF = InlineFont(sz=11, b=True, color=BEYAZ)
GUNDUZ_GOREV = InlineFont(sz=8, color=GRI)
GECE_GOREV = InlineFont(sz=8, color="C9CEE4")     # lacivert zeminde okunur soluk ton


def _hucre_metni(etiket: str, gorevler: str) -> CellRichText:
    harf, gorev = ((GECE_HARF, GECE_GOREV) if etiket == "N"
                   else (GUNDUZ_HARF, GUNDUZ_GOREV))
    return CellRichText(
        TextBlock(harf, etiket),
        TextBlock(gorev, f"\n{gorevler}" if gorevler else "\n"),
    )


def _buyuk(metin: str) -> str:
    """Türkçe büyük harf. Python'un upper()'ı 'i' → 'I' yapıyor, 'İ' olmalı."""
    return metin.replace("i", "İ").replace("ı", "I").upper()


def _tarih(d: date) -> str:
    return f"{d.day} {AY_ADI[d.month - 1]} {d.year}"


def _donem_etiketi(bas: date, son: date) -> str:
    """'Ekim 2026' (tam ay) veya '21–27 Eylül 2026' (kısa dönem)."""
    UZUN_AY = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
               "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    sonraki = date(bas.year + (bas.month == 12), bas.month % 12 + 1, 1)
    if bas.day == 1 and son + timedelta(days=1) == sonraki:
        return f"{UZUN_AY[bas.month - 1]} {bas.year}"
    if bas.month == son.month:
        return f"{bas.day}–{son.day} {UZUN_AY[son.month - 1]} {son.year}"
    return f"{bas.day} {UZUN_AY[bas.month - 1]} – {son.day} {UZUN_AY[son.month - 1]} {son.year}"


def _dosya_adi(parca: str, bas: date, bitis_dis: date) -> str:
    return (f"Acibadem_Nobet_{parca}_{bas:%Y%m%d}-"
            f"{(bitis_dis - timedelta(days=1)):%Y%m%d}.xlsx")


def _yanit(kitap: Workbook, ad: str) -> StreamingResponse:
    akis = BytesIO()
    kitap.save(akis)
    akis.seek(0)
    return StreamingResponse(
        akis,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Türkçe karakterler için RFC 5987: filename* alanı UTF-8 taşır
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(ad)}"},
    )


async def _yukle(draft_id: int) -> tuple[dict, dict, date, date]:
    if (t := await repo.taslak(draft_id)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")
    bas: date = t["period_start"]
    bitis: date = t["period_end"]          # DIŞLAYICI
    veri = await repo.cizelge_verisi(draft_id, bas, bitis - timedelta(days=1))
    return t, veri, bas, bitis


# ---------------------------------------------------------------- çizelge ---

@router.get("/drafts/{draft_id}/export.xlsx", summary="Çizelgeyi Excel'e aktar")
async def excel(draft_id: int) -> StreamingResponse:
    t, veri, bas, bitis = await _yukle(draft_id)
    gunler = [bas + timedelta(days=i) for i in range((bitis - bas).days)]

    kitap = Workbook()
    _sayfa_cizelge(kitap.active, t, gunler, veri)
    return _yanit(kitap, _dosya_adi("Cizelge", bas, bitis))


def _sayfa_cizelge(ws, t: dict, gunler: list[date], veri: dict) -> None:
    ws.title = "Çizelge"
    son_sutun = len(gunler) + 4          # A + günler + 3 toplam sütunu

    # --- Başlık bloğu: kurum · birim · dönem. Taslak adı GİRMEZ (27.09) -----
    ws["A1"] = (f"Acıbadem Kent ASG · {t['unit_name']} — "
                f"{_donem_etiketi(gunler[0], gunler[-1])} Nöbet Çizelgesi")
    ws["A1"].font = Font(bold=True, size=14, color=BRAND)
    # Oluşturulma = taslağın kendi tarihi, dosyanın indirildiği gün değil.
    ws["A2"] = (f"Durum: {DURUM_ADI.get(t['status'], t['status'])} · "
                f"Oluşturulma: {_tarih(t['created_at'].date())}")
    ws["A2"].font = Font(color=GRI, size=10)
    ws["A3"] = ACIKLAMA
    ws["A3"].font = Font(color=GRI, size=9)

    BASLIK = 5
    ws.cell(BASLIK, 1, "Personel").font = Font(bold=True, size=10)
    ws.cell(BASLIK, 1).fill = PatternFill("solid", fgColor=ZEMIN)
    ws.cell(BASLIK, 1).border = KENARLIK
    ws.cell(BASLIK, 1).alignment = Alignment(vertical="center")

    for i, g in enumerate(gunler):
        h = ws.cell(BASLIK, 2 + i, f"{GUN_ADI[g.weekday()]}\n{g.day}")
        h.font = Font(bold=True, size=9)
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        h.fill = PatternFill("solid", fgColor=HAFTASONU if g.weekday() >= 5 else ZEMIN)
        h.border = HAFTA_SONU_KENARLIK if g.weekday() == 6 else KENARLIK

    for j, ad in enumerate(["Toplam saat", "Gece", "Hedefe fark"]):
        h = ws.cell(BASLIK, len(gunler) + 2 + j, ad)
        h.font = Font(bold=True, size=9)
        h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        h.fill = PatternFill("solid", fgColor=ZEMIN)
        h.border = KENARLIK

    atamalar = {(a["staff_id"], a["work_date"]): a for a in veri["atamalar"]}
    izinler: dict[tuple[int, date], str] = {}
    for iz in veri["izinler"]:
        g = iz["period"].lower
        while g < iz["period"].upper:
            izinler[(iz["staff_id"], g)] = iz["absence_type"]
            g += timedelta(days=1)

    ozet = {k["staff_id"]: k for k in rapor.kisi_ozeti(veri, gunler[0], gunler[-1] + timedelta(days=1))}

    # Rol gruplarıyla — ekrandaki düzenin aynısı
    gruplar = [
        ("Sorumlu & Eğitim", {"sorumlu_hemsire", "egitim_hemsire"}),
        ("Ekip Liderleri", {"shift_yetkilisi"}),
        ("Hemşireler", None),
    ]
    ozel = {"sorumlu_hemsire", "egitim_hemsire", "shift_yetkilisi"}
    satir = BASLIK + 1
    for ad, roller in gruplar:
        kisiler = [
            k for k in veri["personel"]
            if (k["role_code"] in roller) if roller is not None
        ] if roller is not None else [
            k for k in veri["personel"] if k["role_code"] not in ozel
        ]
        if not kisiler:
            continue
        b = ws.cell(satir, 1, _buyuk(ad))
        b.font = Font(bold=True, size=9, color=GRI)
        for c in range(1, son_sutun + 1):
            ws.cell(satir, c).fill = PatternFill("solid", fgColor=ZEMIN)
        ws.row_dimensions[satir].height = 16
        satir += 1

        for k in kisiler:
            ad_h = ws.cell(satir, 1, k["full_name"])
            ad_h.border = KENARLIK
            ad_h.font = Font(size=10)
            ad_h.alignment = Alignment(vertical="center")

            for i, g in enumerate(gunler):
                h = ws.cell(satir, 2 + i)
                h.border = HAFTA_SONU_KENARLIK if g.weekday() == 6 else KENARLIK
                h.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                if g.weekday() >= 5:
                    h.fill = PatternFill("solid", fgColor=HAFTASONU)

                a = atamalar.get((k["id"], g))
                if a is not None:
                    # Her hücre iki satır: üstte vardiya harfi, altta görevler.
                    # Görev yoksa bile alt satır boş bırakılır ki hizalama bozulmasın.
                    etiket = VARDIYA_ETIKET.get(a["shift_code"], "G")
                    gorevler = " ".join(GOREV_KISA.get(x, x) for x in (a["tasks"] or []))
                    h.value = _hucre_metni(etiket, gorevler)
                    if etiket == "N":
                        h.fill = PatternFill("solid", fgColor=BRAND)
                elif (k["id"], g) in izinler:
                    h.value = CellRichText(
                        TextBlock(InlineFont(sz=9, color=GRI),
                                  IZIN_ADI.get(izinler[(k["id"], g)], "İzin")),
                        TextBlock(GUNDUZ_GOREV, "\n"),
                    )

            o = ozet.get(k["id"], {})
            for j, deger in enumerate([o.get("total_hours"), o.get("night_count"),
                                       o.get("diff_hours")]):
                h = ws.cell(satir, len(gunler) + 2 + j,
                            deger if deger is not None else "—")
                h.border = KENARLIK
                h.alignment = Alignment(horizontal="center", vertical="center")
                h.font = (Font(color=KIRMIZI, size=10, bold=True)
                          if j == 2 and isinstance(deger, (int, float)) and deger < 0
                          else Font(size=10))
            ws.row_dimensions[satir].height = 26
            satir += 1

    _alt_kapsama(ws, satir + 1, gunler, veri, son_sutun)

    # --- Ölçüler: gün sütunları eşit ve dar, satırlar eşit -------------------
    ws.column_dimensions["A"].width = 22
    for i in range(len(gunler)):
        ws.column_dimensions[get_column_letter(2 + i)].width = 6.4
    for j in range(3):
        ws.column_dimensions[get_column_letter(len(gunler) + 2 + j)].width = 8.5
    ws.row_dimensions[BASLIK].height = 26
    ws.freeze_panes = ws.cell(BASLIK + 1, 2)       # ilk sütun + başlık dondurulur

    # --- Yazdırma: A3 yatay, genişlikte tek sayfa ---------------------------
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.35, bottom=0.45,
                                  header=0.2, footer=0.2)
    ws.print_title_rows = f"1:{BASLIK}"            # başlık bloğu her sayfada
    ws.print_title_cols = "A:A"                    # personel adı her sayfada
    ws.oddFooter.right.text = "Sayfa &P / &N"
    ws.oddFooter.right.size = 8
    ws.oddFooter.right.color = GRI


def _alt_kapsama(ws, satir: int, gunler: list[date], veri: dict, son_sutun: int) -> None:
    """Altta iki satır: her gün 'G atanan/gereken' ve 'N atanan/gereken' (genel mevcut)."""
    genel: dict[tuple[date, str], dict] = {
        (k["day"], k["shift_code"]): k
        for k in veri["kapsama"] if k["slot_code"] == "GENEL"
    }
    for j, (kod, etiket) in enumerate((("GUNDUZ", "G"), ("GECE", "N"))):
        r = satir + j
        b = ws.cell(r, 1, f"{etiket} — atanan / gereken")
        b.font = Font(bold=True, size=9, color=GRI)
        b.border = KENARLIK
        for i, g in enumerate(gunler):
            k = genel.get((g, kod))
            h = ws.cell(r, 2 + i, f"{k['assigned']}/{k['required']}" if k else "—")
            h.border = HAFTA_SONU_KENARLIK if g.weekday() == 6 else KENARLIK
            h.alignment = Alignment(horizontal="center", vertical="center")
            eksik = bool(k) and k["assigned"] < k["required"]
            h.font = Font(size=9, color=KIRMIZI, bold=True) if eksik else Font(size=9, color=GRI)
            if g.weekday() >= 5:
                h.fill = PatternFill("solid", fgColor=HAFTASONU)
        for c in range(len(gunler) + 2, son_sutun + 1):
            ws.cell(r, c).border = KENARLIK
        ws.row_dimensions[r].height = 18


# ------------------------------------------------------- rapor sayfaları ---

def _tablo_sayfasi(ws, basliklar: list[str], satirlar: list[list], genislikler: list[int],
                   baslik: str, alt_baslik: str, kirmizi_kolon: int | None = None) -> None:
    """Raporlar ekranının iki bölümü de aynı biçimde çıkar."""
    ws["A1"] = baslik
    ws["A1"].font = Font(bold=True, size=13, color=BRAND)
    ws["A2"] = alt_baslik
    ws["A2"].font = Font(color=GRI, size=10)

    BASLIK = 4
    for i, b in enumerate(basliklar, start=1):
        h = ws.cell(BASLIK, i, b)
        h.font = Font(bold=True, size=10)
        h.fill = PatternFill("solid", fgColor=ZEMIN)
        h.border = KENARLIK

    for r, degerler in enumerate(satirlar, start=BASLIK + 1):
        for i, d in enumerate(degerler, start=1):
            h = ws.cell(r, i, d)
            h.border = KENARLIK
            h.font = Font(size=10)
            if kirmizi_kolon == i and isinstance(d, (int, float)) and d < 0:
                h.font = Font(size=10, color=KIRMIZI, bold=True)
            elif kirmizi_kolon == i and kirmizi_kolon == len(basliklar) and isinstance(d, int) and d > 0:
                h.font = Font(size=10, color=KIRMIZI, bold=True)

    for i, g in enumerate(genislikler, start=1):
        ws.column_dimensions[get_column_letter(i)].width = g
    ws.freeze_panes = ws.cell(BASLIK + 1, 1)

    ws.page_setup.orientation = "portrait"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = f"{BASLIK}:{BASLIK}"
    ws.oddFooter.right.text = "Sayfa &P / &N"
    ws.oddFooter.right.size = 8


@router.get("/drafts/{draft_id}/export-ozet.xlsx", summary="Kişi özetini Excel'e aktar")
async def excel_ozet(draft_id: int) -> StreamingResponse:
    t, veri, bas, bitis = await _yukle(draft_id)
    satirlar = rapor.kisi_ozeti(veri, bas, bitis)

    kitap = Workbook()
    ws = kitap.active
    ws.title = "Kişi özeti"
    _tablo_sayfasi(
        ws,
        ["Personel", "Rol", "Toplam saat", "Gece", "Hafta sonu", "Hedef", "Fark"],
        [[k["full_name"], k["role_name"], k["total_hours"], k["night_count"],
          k["weekend_count"], k["target_hours"] if k["target_hours"] is not None else "—",
          k["diff_hours"] if k["diff_hours"] is not None else "—"] for k in satirlar],
        [26, 22, 12, 8, 12, 10, 10],
        f"Kişi özeti — {_donem_etiketi(bas, bitis - timedelta(days=1))}",
        " · ".join(x for x in [f"Acıbadem Kent ASG · {t['unit_name']}",
                               rapor.hedef_notu(veri, bas, bitis)] if x),
        kirmizi_kolon=7,
    )
    return _yanit(kitap, _dosya_adi("Kisi_Ozeti", bas, bitis))


@router.get("/drafts/{draft_id}/export-eksikler.xlsx", summary="Eksikleri Excel'e aktar")
async def excel_eksikler(draft_id: int) -> StreamingResponse:
    t, veri, bas, bitis = await _yukle(draft_id)
    satirlar = rapor.eksikler(veri)

    kitap = Workbook()
    ws = kitap.active
    ws.title = "Eksikler"
    _tablo_sayfasi(
        ws,
        ["Gün", "Vardiya", "Görev", "Atanan", "Gereken", "Eksik"],
        [[_tarih(e["day"]), e["shift_name"], e["slot_name"],
          e["assigned"], e["required"], e["missing"]] for e in satirlar]
        or [["Bu dönemde eksik yok.", "", "", "", "", ""]],
        [16, 14, 18, 10, 10, 10],
        f"Eksikler — {_donem_etiketi(bas, bitis - timedelta(days=1))}",
        f"Acıbadem Kent ASG · {t['unit_name']}",
        kirmizi_kolon=6,
    )
    return _yanit(kitap, _dosya_adi("Eksikler", bas, bitis))
