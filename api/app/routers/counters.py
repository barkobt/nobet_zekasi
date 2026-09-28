"""Görünür sayaçlar ekranı + arayüz tercihleri.

Kalıcı ayarların hepsi veritabanında: localStorage kullanılmıyor, böylece sunum
makinesinden ya da başka bir tarayıcıdan aynı görünüm açılır.
"""

from fastapi import APIRouter, HTTPException

from app.repositories import counters as repo
from app.schemas.counters import Counter, CounterList, CounterUpdate, Preference

router = APIRouter(tags=["ayarlar"])

# Kullanıcı kimliği henüz yok (tek paylaşılan parola). Tercihler bu anahtar altında.
VARSAYILAN_KULLANICI = "demo"


@router.get("/counters", response_model=CounterList, summary="Görünür sayaç ayarları")
async def sayaclar() -> CounterList:
    return CounterList(counters=[Counter(**s) for s in await repo.sayaclar()])


@router.put("/counters", response_model=CounterList, summary="Sayaç ayarlarını kaydet")
async def sayaclari_kaydet(guncellemeler: list[CounterUpdate]) -> CounterList:
    mevcut = {s["key"]: s for s in await repo.sayaclar()}
    bilinmeyen = [g.key for g in guncellemeler if g.key not in mevcut]
    if bilinmeyen:
        raise HTTPException(status_code=422, detail=f"Bilinmeyen sayaç: {', '.join(bilinmeyen)}")

    # Her zaman görünen sayaçlar (G · N · S) kapatılamaz — veritabanındaki CHECK de
    # buna izin vermiyor. Sessizce atlamak yerine açıkça söylüyoruz.
    kilitli = [g.key for g in guncellemeler
               if mevcut[g.key]["always_shown"] and not (g.weekly_on and g.monthly_on)]
    if kilitli:
        raise HTTPException(
            status_code=422,
            detail=f"Şu sayaçlar her zaman görünür, kapatılamaz: {', '.join(kilitli)}",
        )

    await repo.sayaclari_yaz([(g.key, g.weekly_on, g.monthly_on) for g in guncellemeler])
    return CounterList(counters=[Counter(**s) for s in await repo.sayaclar()])


@router.get("/prefs/{pref_key}", response_model=Preference, summary="Arayüz tercihi oku")
async def tercih_oku(pref_key: str) -> Preference:
    deger = await repo.tercih(VARSAYILAN_KULLANICI, pref_key)
    return Preference(pref_key=pref_key, value=deger)


@router.put("/prefs/{pref_key}", response_model=Preference, summary="Arayüz tercihi yaz")
async def tercih_yaz(pref_key: str, govde: Preference) -> Preference:
    await repo.tercih_yaz(VARSAYILAN_KULLANICI, pref_key, govde.value)
    return Preference(pref_key=pref_key, value=govde.value)
