"""Eksiklerin sade Türkçe açıklaması (E-10).

Solver bir eksik bulduğunda "kaç kişi eksik" yetmez; "neden" gerekir. Bu modül
çözümü okuyup aday havuzundaki herkesi TEK bir sebebe yerleştirir ve cümleyi kurar:

    15 Eki 2026 · Gece triyaj: 1 kişi eksik (2/3). Gece çalışabilen 10 triyaj
    yetkilisinden 3'ü izinli, 4'ü 2 gece sonrası dinlenmede, 2'si o gün gündüzde.

İKİ ÖNEMLİ NOT:
  1. Dinlenme sebepleri (C-002, C-014, C-016) BU ÇÖZÜME GÖRE doğrudur, mutlak
     değil: o kişi başka bir çizelgede müsait olabilirdi. Metin "dinlenmede" der,
     "dinlenmek zorundaydı" demez.
  2. "Müsaitti" kategorisi şart. Sıfırdan büyükse eksiğin sebebi müsaitlik
     değildir — başka bir kural (triyaj/gözlem bölmesi, aynı vardiyadaki başka
     slot) o kişiyi engelliyordur ve cümle bunu söyler. Yazmazsak açıklama
     yanıltıcı olur.

E-10 teşhisleri kural adına göre gruplayıp yalnız `message` alanını gösteriyor
(kural başına 3 örnek). Bu yüzden sebep cümlesi `message`'a giriyor; `suggestion`
eyleme dönük öneri olarak kalıyor.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from solver.data import SolverVerisi

# Sayıya iyelik eki: "3'ü", "2'si", "10'u". Havuzlar küçük, 1-30 yeterli.
_BIRLER = {1: "i", 2: "si", 3: "ü", 4: "ü", 5: "i", 6: "sı", 7: "si", 8: "i", 9: "u"}
_ONLAR = {10: "u", 20: "si", 30: "u"}

VARDIYA_ADI = {"GUNDUZ": "Gündüz", "GECE": "Gece", "GUNDUZ_CMT": "Gündüz (Cmt)"}
SLOT_ADI = {
    "GENEL": "genel mevcut", "TRIYAJ": "triyaj", "GOZLEM": "gözlem",
    "AMBULANS": "ambulans", "SAYIM": "sayım yetkilisi",
    "SHIFT_YETKILISI": "ekip lideri", "ROZETSIZ": "rozetsiz çalışan",
}


def saat(dk: int) -> str:
    """Dakikayı Türkçe biçimde saate çevirir: 1110 → "18,5".

    Tek ondalık BİLEREK: gündüzün neti 8 sa 10 dk, saat cinsinden 8,1666…
    Hemşireye "8,17 saat" demek anlamsız; metin zaten yaklaşık değer verir.
    Hesap hiçbir yerde bu metinden geçmez, dakikayla yapılır.
    """
    return f"{dk / 60:.1f}".replace(".", ",").removesuffix(",0")


def sayiyla(n: int) -> str:
    """3 → "3'ü", 2 → "2'si"."""
    ek = _ONLAR.get(n) or _BIRLER.get(n % 10 if n >= 10 else n, "i")
    return f"{n}'{ek}"


class Cozumun(dict):
    """Çözümün kişi-gün-vardiya görünümü. Açıklama üretimi hep buradan sorar."""

    def __init__(self, v: SolverVerisi, atamalar, rozetler):
        super().__init__()
        self.gece_kodlari = {s.kod for s in v.vardiyalar if s.gece_mi}
        self.plan: dict[tuple[int, date], str] = {}
        for p_id, g, kod in atamalar:
            self.plan[p_id, g] = kod
        for a in v.gecmis:                       # geçmiş 7 gün de plana dahil
            self.plan.setdefault((a.personel_id, a.gun), a.vardiya_kodu)
        for s in v.sabit_atamalar:
            self.plan.setdefault((s.personel_id, s.gun), s.vardiya_kodu)
        self.rozet: dict[tuple[int, date], set[str]] = {}
        for p_id, g, _vd, gorev in rozetler:
            self.rozet.setdefault((p_id, g), set()).add(gorev)

    def vardiya(self, p_id: int, g: date) -> str | None:
        return self.plan.get((p_id, g))

    def gece_mi(self, p_id: int, g: date) -> bool:
        return self.plan.get((p_id, g)) in self.gece_kodlari

    def calisiyor(self, p_id: int, g: date) -> bool:
        return (p_id, g) in self.plan


def _havuz(v: SolverVerisi, slot: str, vardiya_kodu: str) -> tuple[list, str]:
    """Slotun aday havuzu ve havuzu anlatan kısa ad."""
    vardiya = next(s for s in v.vardiyalar if s.kod == vardiya_kodu)
    calisabilir = [
        p for p in v.personel
        if not (vardiya.gece_mi and p.uygunluk == "sadece_gunduz")
        and not (not vardiya.gece_mi and p.uygunluk == "sadece_gece")
    ]
    tip = "Gece çalışabilen" if vardiya.gece_mi else "Gündüz çalışabilen"

    if slot in ("SAYIM", "SHIFT_YETKILISI"):
        # Yetkinlik slotu: sorumlu ve oryantasyondakiler de sayılır (v_daily_coverage)
        havuz = [p for p in calisabilir if slot in p.yetkinlikler]
        return havuz, f"{tip} {len(havuz)} {SLOT_ADI[slot]}"
    if slot == "GENEL":
        havuz = [p for p in calisabilir if p.kapsamaya_sayilir]
        return havuz, f"{tip} {len(havuz)} kişi"
    havuz = [p for p in calisabilir if p.kapsamaya_sayilir and slot in p.yetkinlikler]
    return havuz, f"{tip} {len(havuz)} {SLOT_ADI[slot]} yetkilisi"


def _neden(v: SolverVerisi, c: Cozumun, p, g: date, vardiya_kodu: str,
           izinli: set, onayli: set, hafta: dict) -> str:
    """Adayın o gün o vardiyada NEDEN olmadığı. İlk eşleşen sebep kazanır."""
    gece_mi = vardiya_kodu in c.gece_kodlari
    if (p.id, g) in izinli:
        return "izinli"
    if (p.id, g, "BOS_GUN") in onayli:
        return "kesin izin isteği var"
    if gece_mi and (p.id, g, "SADECE_GUNDUZ") in onayli:
        return "kesin gündüz isteği var"
    if not gece_mi and (p.id, g, "SADECE_GECE") in onayli:
        return "kesin gece isteği var"
    if c.calisiyor(p.id, g):
        # Aynı vardiyada ama bu slotta değil: çalışıyor, görevi başka. "O gün
        # gecede" demek gece eksiğinde kafa karıştırırdı.
        if c.vardiya(p.id, g) == vardiya_kodu:
            return "aynı vardiyada başka görevde"
        return "o gün gecede" if c.gece_mi(p.id, g) else "o gün gündüzde"
    # C-014: iki gün öncesi ve dünü gece → bugün hiç çalışamaz
    if c.gece_mi(p.id, g - timedelta(days=2)) and c.gece_mi(p.id, g - timedelta(days=1)):
        return "2 gece sonrası dinlenmede"
    # C-002: bu gece 3. gece olurdu
    if gece_mi:
        komsu = [
            (g - timedelta(days=2), g - timedelta(days=1)),
            (g - timedelta(days=1), g + timedelta(days=1)),
            (g + timedelta(days=1), g + timedelta(days=2)),
        ]
        if any(c.gece_mi(p.id, a) and c.gece_mi(p.id, b) for a, b in komsu):
            return "3. gece olurdu"
    # C-016: haftanın tek boş günü
    pzt = g - timedelta(days=g.weekday())
    gunler = hafta.get(pzt, [])
    if gunler and sum(1 for x in gunler if not c.calisiyor(p.id, x)) == 1:
        return "haftalık izin günü"
    return "müsaitti"


def eksik_aciklamalari(v: SolverVerisi, cozum, run_id: int) -> list[tuple]:
    """Her kapsama/görev eksiği için bir teşhis satırı."""
    c = Cozumun(v, cozum.atamalar, cozum.rozetler)
    izinli = {(y.personel_id, y.gun) for y in v.yokluklar}
    onayli = {(i.personel_id, i.gun, i.tur) for i in v.kesin_istekler}
    donem = set(v.gunler)
    hafta: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        hafta.setdefault(pzt, [x for x in (pzt + timedelta(days=i) for i in range(7))
                               if x in donem])

    satirlar = []
    for e in sorted(cozum.eksikler, key=lambda k: (k.gun, k.vardiya_kodu, k.slot)):
        kural = v.kurallar.get(e.kural_kodu) if e.kural_kodu else None
        vardiya = VARDIYA_ADI.get(e.vardiya_kodu, e.vardiya_kodu)
        slot = SLOT_ADI.get(e.slot, e.slot)

        if e.slot == "ROZETSIZ":
            mesaj = (f"{vardiya}: {e.adet} kişi ne triyajda ne gözlemde."
                     " Triyaj ve gözlem alanları dolu ya da bu kişilerin"
                     " ikisine de yetkinliği yok.")
            satirlar.append((run_id, "ihlal", kural.id if kural else None, e.gun, mesaj,
                             "Vardiyadaki herkes ya triyajda ya gözlemde olmalı."))
            continue

        havuz, havuz_adi = _havuz(v, e.slot, e.vardiya_kodu)
        atanan = e.gereken - e.adet
        sebepler = Counter()
        for p in havuz:
            if c.vardiya(p.id, e.gun) == e.vardiya_kodu and (
                e.slot in ("GENEL", "SAYIM", "SHIFT_YETKILISI")
                or e.slot in c.rozet.get((p.id, e.gun), ())
            ):
                continue                                   # bu kişi zaten sayılıyor
            sebepler[_neden(v, c, p, e.gun, e.vardiya_kodu, izinli, onayli, hafta)] += 1

        parcalar = [f"{sayiyla(adet)} {sebep}"
                    for sebep, adet in sebepler.most_common() if sebep != "müsaitti"]
        musait = sebepler.get("müsaitti", 0)
        mesaj = f"{vardiya} {slot}: {e.adet} kişi eksik ({atanan}/{e.gereken})."
        if parcalar:
            mesaj += f" {havuz_adi}den " + ", ".join(parcalar) + "."
        if musait:
            mesaj += (f" {sayiyla(musait)} müsaitti; eksik müsaitlikten değil,"
                      " başka bir kuraldan kaynaklanıyor.")
        satirlar.append((
            run_id, "ihlal", kural.id if kural else None, e.gun, mesaj,
            "İzinleri gözden geçirin, yetkin personel ekleyin veya ihtiyaç"
            " şablonundaki sayıyı düşürün.",
        ))
    return satirlar


def saat_aciklamalari(v: SolverVerisi, cozum, run_id: int) -> list[tuple]:
    """C-004: aylık hedefe ulaşamayanlar, sebebiyle."""
    kural = v.kural("C-004")
    c = Cozumun(v, cozum.atamalar, cozum.rozetler)
    izinli = Counter(y.personel_id for y in v.yokluklar)
    ad = {p.id: p.ad for p in v.personel}
    satirlar = []
    for p_id, eksik_dk in sorted(cozum.saat_eksikleri.items(), key=lambda t: -t[1]):
        bos = sum(1 for g in v.gunler if not c.calisiyor(p_id, g))
        kisi = next(p for p in v.personel if p.id == p_id)
        tip = {"sadece_gunduz": ", yalnız gündüz çalışabiliyor",
               "sadece_gece": ", yalnız gece çalışabiliyor"}.get(kisi.uygunluk, "")
        mesaj = (f"{ad[p_id]}: aylık hedefin {saat(eksik_dk)} saat altında."
                 f" Dönemde {izinli[p_id]} gün izinli, {bos} gün boş{tip}.")
        satirlar.append((run_id, "ihlal", kural.id if kural else None, None, mesaj,
                         "Kişinin çalışma tipi, yetkinlikleri ya da dinlenme"
                         " kuralları daha fazla vardiya almasını engelliyor."))
    return satirlar


def takviye_aciklamalari(v: SolverVerisi, cozum, run_id: int) -> list[tuple]:
    """C-022: acil takviye olarak yazılan oryantasyondaki personel."""
    kural = v.kural("C-022")
    ad = {p.id: p.ad for p in v.personel}
    satirlar = []
    for p_id, g, vardiya_kodu in sorted(getattr(cozum, "takviyeler", []), key=lambda k: (k[1], k[0])):
        vardiya = VARDIYA_ADI.get(vardiya_kodu, vardiya_kodu)
        satirlar.append((
            run_id, "uyari", kural.id if kural else None, g,
            f"{vardiya}: {ad[p_id]} (oryantasyon) acil takviye olarak yazıldı.",
            "Genel mevcut başka türlü tamamlanamadı. Oryantasyondaki kişi ambulansa"
            " çıkmaz ve alanda yalnız bırakılmaz.",
        ))
    return satirlar


def istek_aciklamalari(v: SolverVerisi, cozum, run_id: int) -> list[tuple]:
    """O-006: karşılanamayan "mümkünse" tercihleri."""
    kural = v.kural("O-006")
    ad = {p.id: p.ad for p in v.personel}
    tur_adi = {"BOS_GUN": "boş gün", "SADECE_GUNDUZ": "yalnız gündüz",
               "SADECE_GECE": "yalnız gece"}
    satirlar = []
    for p_id, g, tur in sorted(cozum.karsilanmayan_istekler, key=lambda t: (t[1], t[0])):
        mesaj = f"{ad[p_id]}: {tur_adi.get(tur, tur)} tercihi karşılanamadı (mümkünse)."
        satirlar.append((run_id, "ihlal", kural.id if kural else None, g, mesaj,
                         "İstek KESIN yapılırsa katı kural olur; bu haliyle yalnız"
                         " tercih olarak değerlendirildi."))
    return satirlar
