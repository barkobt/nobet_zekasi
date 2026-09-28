"""Dönem hedef saati.

27.09 kararı: **orantılı hesap yok.** Daha önce aylık 200 saat dönem gün
sayısına bölünüyordu ve bir haftalık taslakta "46,7 saat" gibi kimsenin
tanımadığı bir sayı çıkıyordu. Artık yalnız iki tanınan dönem var:

  * tam takvim ayı  → C-004 aylık asgari (constraint_params: monthly_min_hours)
  * tam 7 gün       → C-003 haftalık referans (constraint_params: weekly_reference_hours)

Başka uzunluktaki bir dönemde hedef **gösterilmez** (None) — uydurulmuş bir
sayı göstermektense boş bırakmak doğru (DESIGN §7).

Sayılar koda gömülü değil; ikisi de veritabanından gelir.
"""

from datetime import date


def donem_turu(bas: date, bitis_dis: date) -> str:
    """'ay' | 'hafta' | 'diger'. bitis_dis DIŞLAYICI (upper(period))."""
    sonraki_ay = date(bas.year + (bas.month == 12), bas.month % 12 + 1, 1)
    if bas.day == 1 and bitis_dis == sonraki_ay:
        return "ay"
    if (bitis_dis - bas).days == 7:
        return "hafta"
    return "diger"


def donem_hedefi(tur: str, aylik_min: float | None, haftalik_ref: float | None) -> float | None:
    if tur == "ay":
        return float(aylik_min) if aylik_min else None
    if tur == "hafta":
        return float(haftalik_ref) if haftalik_ref else None
    return None


def izin_dusumu(hedef: float | None, izin_gunu: int, gunluk_dusum: float | None) -> float | None:
    """Aylık hedeften izin/rapor günlerini düşer (C-004 parametresi).

    Solver aynı hesabı yapıyor (solver/model.py, absence_daily_reduction_hours):
    ekranın 200 deyip çözücünün 125 istemesi, izinli birini eksik çalışmış gibi
    gösterirdi. Haftalık referansta (C-003) düşüm YOK — o kural izni tanımıyor.
    """
    if hedef is None or not gunluk_dusum or izin_gunu <= 0:
        return hedef
    return max(0.0, round(hedef - izin_gunu * float(gunluk_dusum), 1))


def hedef_etiketi(tur: str, hedef: float | None) -> str | None:
    """Ekranda ve Excel'de hedefin ne olduğunu söyleyen tek cümlelik etiket."""
    if hedef is None:
        return None
    return f"Aylık hedef {hedef:g} sa" if tur == "ay" else f"Haftalık hedef {hedef:g} sa"
