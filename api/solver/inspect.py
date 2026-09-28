"""Kontrol komutu: `uv run python -m solver.inspect <draft_id>`

data.py'nin okuduğunu sade Türkçeyle döker. Hiçbir şey yazmaz, model kurmaz.
Amacı, modele girmeden önce "veri doğru mu, çözülebilir mi" sorusunu gözle
cevaplamak: kaç kişi kapsamaya sayılıyor, hangi yetkinlikten kaç kişi var,
talep edilen saat ile hedef saatler yan yana nasıl duruyor.
"""

from __future__ import annotations

import sys
from collections import Counter

from solver.data import ISTEK_TURLERI, SolverVerisi, veriyi_oku

AYLAR = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")
GUNLER = ("Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz")
UYGUNLUK = {
    "gunduz_gece": "gündüz+gece",
    "sadece_gunduz": "sadece gündüz",
    "sadece_gece": "sadece gece",
}


def tarih(gun) -> str:
    return f"{gun.day} {AYLAR[gun.month - 1]} {gun.year}"


def kisa_tarih(gun) -> str:
    return f"{gun.day:2d} {AYLAR[gun.month - 1]} {GUNLER[gun.weekday()]}"


def saat(yb: int) -> str:
    """Yarım saat birimini okunur saate çevirir: 7440 → '3.720', 437 → '218,5'."""
    metin = f"{yb / 2:,.1f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return metin.removesuffix(",0")


def baslik(metin: str) -> None:
    print(f"\n{metin}\n{'─' * len(metin)}")


# ---------------------------------------------------------------------------


def taslak_ozeti(v: SolverVerisi) -> None:
    baslik("TASLAK")
    print(f"  #{v.draft_id} · {v.taslak_adi}")
    print(
        f"  Dönem: {tarih(v.donem_bas)} – {tarih(v.gunler[-1])}"
        f"  ({len(v.gunler)} gün; üst sınır {tarih(v.donem_bit)} dahil DEĞİL)"
    )


def vardiya_ozeti(v: SolverVerisi) -> None:
    baslik("VARDİYALAR (aktif olanlar)")
    for s in v.vardiyalar:
        etiket = "gece" if s.gece_mi else "gündüz"
        satir = (
            f"  {s.kod:<11} {s.baslangic.strftime('%H:%M')} · {saat(s.sure_yb):>5} sa"
            f" ({s.sure_yb} yb) · {etiket}"
        )
        if s.sadece_rol or s.sadece_hafta_gunleri:
            gunler = (
                ", ".join(GUNLER[g - 1] for g in sorted(s.sadece_hafta_gunleri))
                if s.sadece_hafta_gunleri
                else "her gün"
            )
            satir += f"  ⟵ yalnız {s.sadece_rol}, yalnız {gunler}"
        print(satir)
    print("  (pasif 24 saatlik vardiyalar okunmadı — C-018)")


def personel_ozeti(v: SolverVerisi) -> None:
    sayilan = [p for p in v.personel if p.kapsamaya_sayilir]
    sayilmayan = [p for p in v.personel if not p.kapsamaya_sayilir]

    baslik(f"PERSONEL ({len(v.personel)} aktif kişi)")
    print(f"  {'Ad':<16} {'Rol':<16} {'Çalışma':<14} {'Hedef':>8}  Kapsama")
    for p in v.personel:
        kapsama = "✓ sayılır" if p.kapsamaya_sayilir else f"✗ {p.kapsama_disi_nedeni}"
        yildiz = "" if p.hedef_kaynagi == "sozlesme" else "*"
        print(
            f"  {p.ad:<16} {p.rol_kodu:<16} {UYGUNLUK[p.uygunluk]:<14}"
            f" {saat(p.hedef_saat_yb) + yildiz:>8}  {kapsama}"
        )
    print("  * hedef sözleşmede boş → kural varsayılanı (monthly_min_hours)")

    print(f"\n  Kapsamaya (GENEL mevcut) sayılan: {len(sayilan)} kişi")
    print(f"  Sayılmayan: {len(sayilmayan)} kişi — migration 009 kararı")
    for p in sayilmayan:
        ek = ""
        if p.oryantasyonda and p.buddy_id:
            ek = f" (eşi: {v.kisi(p.buddy_id).ad})"
        print(f"    · {p.ad} — {p.kapsama_disi_nedeni}{ek}")


def yetkinlik_ozeti(v: SolverVerisi) -> None:
    baslik("YETKİNLİK BAŞINA KİŞİ SAYISI")
    sayac: Counter[str] = Counter()
    sayilan_sayac: Counter[str] = Counter()
    for p in v.personel:
        for k in p.yetkinlikler:
            sayac[k] += 1
            if p.kapsamaya_sayilir:
                sayilan_sayac[k] += 1
    print(f"  {'Yetkinlik':<18} {'Tümü':>6} {'Kapsamaya sayılanlar':>22}")
    for kod, adet in sorted(sayac.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {kod:<18} {adet:>6} {sayilan_sayac[kod]:>22}")


def gece_kapasitesi(v: SolverVerisi) -> None:
    """Gece yükünü kim taşıyabilir? Yetkinlik başına gece çalışabilen kişi ve kişi başı gece."""
    gece_vardiyalari = {s.kod for s in v.vardiyalar if s.gece_mi}
    # "Gece çalışabilen" = sadece_gunduz OLMAYAN. Kapsamaya sayılmayanlar (sorumlu,
    # oryantasyon) burada da yok: gece mevcuduna sayılmıyorlar.
    gece_havuzu = [
        p for p in v.personel if p.kapsamaya_sayilir and p.uygunluk != "sadece_gunduz"
    ]

    baslik("GECE KAPASİTESİ — yetkinlik başına gece çalışabilen kişi")
    sayac: Counter[str] = Counter()
    kapsama: Counter[str] = Counter()
    for p in v.personel:
        for k in p.yetkinlikler:
            if p.kapsamaya_sayilir:
                kapsama[k] += 1
                if p.uygunluk != "sadece_gunduz":
                    sayac[k] += 1
    print(f"  {'Yetkinlik':<18} {'Kapsamaya sayılan':>18} {'Gece çalışabilen':>18} {'Fark':>6}")
    for kod in sorted(kapsama, key=lambda k: (-sayac[k], k)):
        print(f"  {kod:<18} {kapsama[kod]:>18} {sayac[kod]:>18} {kapsama[kod] - sayac[kod]:>6}")
    print(f"  {'(yetkinlik şartsız)':<18} {len([p for p in v.personel if p.kapsamaya_sayilir]):>18}"
          f" {len(gece_havuzu):>18} {len([p for p in v.personel if p.kapsamaya_sayilir]) - len(gece_havuzu):>6}")

    baslik("GECE İHTİYACI — kişi başı düşen gece sayısı")
    print(f"  {'Slot':<16} {'Kişi/gece':>9} {'Toplam slot':>12} {'Havuz':>6} {'Kişi başı gece':>15}")
    for i in v.ihtiyaclar:
        if i.vardiya_kodu not in gece_vardiyalari:
            continue
        toplam = i.min_sayi * len(i.gunler)
        # Slotun istediği TÜM yetkinliklere sahip, gece çalışabilen kişiler.
        # TASK da QUALIFICATION da staff_competencies'ten okunur: "bu görevi
        # alabilir mi" ile "bu yetkiye sahip mi" aynı tabloda duruyor.
        istenen = {y.kod for y in i.yetkinlikler}
        havuz = [p for p in gece_havuzu if istenen <= p.yetkinlikler]
        if havuz:
            kisi_basi = f"{toplam / len(havuz):.1f}".replace(".", ",")
        else:
            kisi_basi = "— (havuz BOŞ)"
        print(f"  {i.slot_kodu:<16} {i.min_sayi:>9} {toplam:>12} {len(havuz):>6} {kisi_basi:>15}")
    print(f"  Dönem {len(v.gunler)} gün → bir kişi en çok {len(v.gunler)} gece çalışabilir"
          " (C-002 ardışık sınırı bunu fiilen çok daha aşağı çeker).")


def ihtiyac_ozeti(v: SolverVerisi) -> None:
    baslik("İHTİYAÇ SATIRLARI")
    print(f"  {'Vardiya':<11} {'Slot':<16} {'Kişi':>4}  {'Kural':<32} Tip     Yetkinlik")
    for i in v.ihtiyaclar:
        kural = f"{i.katalog_kodu or '—':<6} {i.kural_kodu or 'bağlı değil'}"
        tip = "hard" if i.hard_mi else f"soft/{i.agirlik}"
        yetk = ", ".join(f"{y.kod}({y.kind[0]})" for y in i.yetkinlikler) or "şart yok"
        gun_notu = "" if len(i.gunler) == len(v.gunler) else f"  [{len(i.gunler)} gün]"
        print(f"  {i.vardiya_kodu:<11} {i.slot_kodu:<16} {i.min_sayi:>4}  {kural:<32} {tip:<7} {yetk}{gun_notu}")
    print("  Yetkinlik tipi: (T)=görev, vardiya içinde atanır · (Q)=kişinin yetkisi, verilidir")


def kural_ozeti(v: SolverVerisi) -> None:
    hard = [k for k in v.kurallar.values() if k.hard_mi]
    soft = [k for k in v.kurallar.values() if not k.hard_mi]
    baslik(f"KURALLAR ({len(hard)} katı, {len(soft)} yumuşak)")
    for grup, ad in ((hard, "KATI"), (soft, "YUMUŞAK")):
        print(f"  — {ad} —")
        for k in sorted(grup, key=lambda x: (x.katalog_kodu or "zzz", x.kod)):
            agirlik = "" if k.hard_mi else f" · ağırlık {k.agirlik}"
            print(f"  {k.katalog_kodu or '—':<6} {k.kod:<32} {k.kapsam:<8} {k.kaynak:<10}{agirlik}")
            for anahtar, deger in k.parametreler.items():
                print(f"         {anahtar} = {format(deger.normalize(), 'f')}")
    print("  Not: constraints'te açık/kapalı kolonu yok — tabloda satırı olan kural açıktır.")


def yokluk_ozeti(v: SolverVerisi) -> None:
    baslik("İZİN / RAPOR (hedefi DÜŞÜRÜR) ve UYUMSUZ ÇİFTLER")
    if v.yokluklar:
        gun_sayisi: Counter[int] = Counter(y.personel_id for y in v.yokluklar)
        for pid, adet in sorted(gun_sayisi.items(), key=lambda x: -x[1]):
            turler = ", ".join(sorted({y.tur for y in v.yokluklar if y.personel_id == pid}))
            print(f"  {v.kisi(pid).ad:<16} {adet:>2} gün  ({turler})")
        print("  Düşüm miktarı henüz belirlenmedi → ham hedef yazıldı (bkz. Sorular)")
    else:
        print("  İzin/rapor kaydı yok (absences tablosu boş) → hiçbir hedef düşmüyor.")

    if v.uyumsuz_ciftler:
        for a, b in v.uyumsuz_ciftler:
            print(f"  uyumsuz: {v.kisi(a).ad} ↮ {v.kisi(b).ad}")
    else:
        print("  Uyumsuz kişi çifti yok (staff_conflicts tablosu boş).")


def istek_ozeti(v: SolverVerisi) -> None:
    """İstekler: KESIN katı kural, MUMKUNSE cezalı tercih. Hedefi DÜŞÜRMEZ."""
    baslik("İSTEKLER (Requests) — 200 saat hedefini DÜŞÜRMEZ")
    print(f"  Kesin (KESIN, modele kısıt): {len(v.kesin_istekler)}")
    for i in v.kesin_istekler:
        print(f"    · {v.kisi(i.personel_id).ad:<16} {kisa_tarih(i.gun)}  {i.tur}")
    print(f"  Mümkünse (MUMKUNSE, cezalı): {len(v.tercih_istekler)}")
    for i in v.tercih_istekler:
        print(f"    · {v.kisi(i.personel_id).ad:<16} {kisa_tarih(i.gun)}  {i.tur}")

    tumu = v.kesin_istekler + v.tercih_istekler
    if not tumu:
        print("  Kayıt yok (availability_rules tablosu boş).")
    bilinmeyen = sorted({i.tur for i in tumu if i.tur not in ISTEK_TURLERI})
    if bilinmeyen:
        print(f"  ⚠ Yeni sözlükte karşılığı olmayan tür(ler): {', '.join(bilinmeyen)}"
              " — solver bunları yorumlamaz.")


def saat_dengesi(v: SolverVerisi) -> None:
    """Talep, kapsama personelinin hedefi, fark. Talep YALNIZ GENEL slotlarından gelir."""
    # C-019: TRIYAJ / AMBULANS / GOZLEM / SAYIM / SHIFT_YETKILISI slotları vardiya
    # mevcudunun İÇİNDEN atanır, ek kadro değildir. O yüzden saat talebine GENEL
    # slotları girer; diğerleri girseydi aynı kişi iki kez sayılırdı.
    talep_yb = 0
    icinden = []
    for i in v.ihtiyaclar:
        if i.slot_kodu == "GENEL":
            talep_yb += i.min_sayi * v.vardiya(i.vardiya_kodu).sure_yb * len(i.gunler)
        else:
            icinden.append(f"{i.vardiya_kodu}/{i.slot_kodu}×{i.min_sayi}")

    sayilan = [p for p in v.personel if p.kapsamaya_sayilir]
    disi = [p for p in v.personel if not p.kapsamaya_sayilir]
    hedef_yb = sum(p.hedef_saat_yb for p in sayilan)
    fark_yb = talep_yb - hedef_yb

    baslik("SAAT DENGESİ")
    print(f"  Talep (GENEL mevcut × süre × gün)            {saat(talep_yb):>9} sa")
    print(f"  Kapsamaya sayılan {len(sayilan)} kişinin hedefi toplamı  {saat(hedef_yb):>9} sa")
    # C-004 bir ASGARİ'dir ("en az 200 saat"), tavan değil. Talep asgarinin üstündeyse
    # bu bir eksiklik değil, O-001'in cezalandıracağı fazla mesaidir. Altındaysa
    # tersi tehlikeli: kimse 200 saate ulaşamaz, C-004 katı olduğu için model çözülemez.
    yorum = (
        "asgarinin ÜSTÜNDE → O-001 fazla mesai olarak cezalandırır"
        if fark_yb >= 0
        else "asgarinin ALTINDA → C-004 katı, kimse 200 saate ulaşamaz"
    )
    isaretli = ("+" if fark_yb >= 0 else "−") + saat(abs(fark_yb))
    print(f"  Fark (talep − hedef)                         {isaretli:>9} sa  {yorum}")
    print(f"  Kişi başı gereken ortalama                   {saat(round(talep_yb / len(sayilan))):>9} sa"
          f"   (hedef {saat(round(hedef_yb / len(sayilan)))} sa)")
    print(f"\n  Kapsama dışındakilerin hedefi (talebe sayılmadı): {saat(sum(p.hedef_saat_yb for p in disi))} sa")
    for p in disi:
        print(f"    · {p.ad:<16} {saat(p.hedef_saat_yb):>6} sa — {p.kapsama_disi_nedeni}")
    print(f"\n  Mevcudun içinden atanan slotlar (C-019, talebe eklenmez): {', '.join(icinden)}")


def gecmis_ozeti(v: SolverVerisi) -> None:
    esik = v.donem_bas
    baslik(f"GEÇMİŞ 7 GÜN — değiştirilemez ({len(v.gecmis)} atama)")
    if not v.gecmis:
        print("  Kayıt yok: ne bağlam satırı (source='onceki_ay') ne yayınlanmış çizelge var.")
    else:
        kaynaklar = Counter(g.kaynak for g in v.gecmis)
        print(f"  Kaynak: {', '.join(f'{k}={a}' for k, a in kaynaklar.items())}")
        print(f"  {'Kişi':<16} {'Gün':<13} Vardiya")
        for g in sorted(v.gecmis, key=lambda x: (x.gun, v.kisi(x.personel_id).ad)):
            gece = " (gece)" if g.gece_mi else ""
            print(f"  {v.kisi(g.personel_id).ad:<16} {kisa_tarih(g.gun):<13} {g.vardiya_kodu}{gece}")

    baslik("AYNI AYDA, DÖNEMDEN ÖNCE ÇALIŞILMIŞ SAAT")
    if not v.ay_basi_saatler_yb:
        print(f"  Boş: dönem ayın 1'inde başlıyor ({tarih(esik)}), öncesi bu aya ait değil.")
    else:
        for pid, yb in sorted(v.ay_basi_saatler_yb.items(), key=lambda x: -x[1]):
            print(f"  {v.kisi(pid).ad:<16} {saat(yb):>6} sa")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Kullanım: uv run python -m solver.inspect <draft_id>", file=sys.stderr)
        return 2
    v = veriyi_oku(int(argv[1]))
    taslak_ozeti(v)
    vardiya_ozeti(v)
    personel_ozeti(v)
    yetkinlik_ozeti(v)
    gece_kapasitesi(v)
    ihtiyac_ozeti(v)
    kural_ozeti(v)
    yokluk_ozeti(v)
    istek_ozeti(v)
    saat_dengesi(v)
    gecmis_ozeti(v)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
