"""Kontrolcü: bir taslağın veritabanındaki atamalarını kurallara göre yargılar.

    uv run python -m solver.validate <draft_id>

BİLEREK model.py ile kod PAYLAŞMAZ. Aynı yardımcı fonksiyonları kullansaydı
modeldeki bir hata kontrolcüde de görünmez olurdu; kontrolcünün tek değeri
bağımsız olmasıdır. Solver'ı hiç çağırmaz, veritabanına hiç yazmaz.

data.py'den yalnız HAM veriyi alır (personel, vardiya, izin, istek, kural,
geçmiş). Taslağın atamalarını kendi sorgusuyla okur — atamalar solver'ın
çıktısıdır, girdisi değil.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

import psycopg
from psycopg.rows import dict_row

from app.settings import get_settings
from solver.data import SolverVerisi, veriyi_oku
from solver.inspect import GUNLER, baslik, kisa_tarih, tarih

GECMIS_GUN = 7
C016_ASGARI_BILINEN_GUN = 4   # bkz. solver/model.py
SORUMLU_ROL = "sorumlu_hemsire"


# KATI kurallar: solver bunları ASLA ihlal etmemeli. Kontrolcü burada bir şey
# bulursa modelde hata var demektir — koşu sonunda 'hata' teşhisi yazılır.
# Listede OLMAYANLAR gevşetilebilir slot asgarileridir (D-1, D-2, D-5, D-6, D-7):
# kadro yetmediğinde eksik kalmaları beklenen davranıştır ve solver zaten
# kendi teşhisinde bildirir.
KATI_KURALLAR = frozenset({
    "A-1", "A-2", "A-3", "A-4", "A-5", "A-6", "A-7",
    "C-002", "C-014", "C-021", "C-016", "C-020", "C-023", "C-024",
    "C-025", "C-026", "C-027", "C-028",
    "D-3", "D-8", "D-9", "D-11",
})


@dataclass(frozen=True)
class Ihlal:
    kod: str                 # A-1, C-002 …
    kural: str               # okunur ad
    personel: str
    gun: date | None
    aciklama: str
    seviye_ustu: str | None = None    # açıkça verilmişse koddan türetmeyi ezer

    @property
    def seviye(self) -> str:
        """kati: model hatası · uyari: elle yapılmış istisna · gevsek: kadro eksiği."""
        if self.seviye_ustu:
            return self.seviye_ustu
        return "kati" if self.kod in KATI_KURALLAR else "gevsek"

    @property
    def kati(self) -> bool:
        return self.seviye == "kati"


def atamalari_oku(draft_id: int) -> list[dict]:
    """Taslağın DÖNEM İÇİNDEKİ atamaları. Dönem dışı satırlar bağlamdır, çizelge değil."""
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.staff_id, a.work_date, st.code AS vardiya_kodu,
                       st.crosses_midnight, a.source, a.is_locked,
                       coalesce(array_agg(c.code) FILTER (WHERE c.code IS NOT NULL),
                                '{}') AS gorevler
                FROM assignments a
                JOIN schedule_drafts d ON d.id = a.draft_id
                JOIN shift_types st    ON st.id = a.shift_type_id
                LEFT JOIN assignment_tasks t ON t.assignment_id = a.id
                LEFT JOIN competencies c     ON c.id = t.competency_id
                WHERE a.draft_id = %s AND d.period @> a.work_date
                GROUP BY a.staff_id, a.work_date, st.code, st.crosses_midnight,
                         a.source, a.is_locked
                ORDER BY a.work_date, a.staff_id
                """,
                (draft_id,),
            )
            return cur.fetchall()


def kontrol_et(v: SolverVerisi, atamalar: list[dict]) -> list[Ihlal]:
    ad = {p.id: p.ad for p in v.personel}
    kisi = {p.id: p for p in v.personel}
    gece_kodlari = {s.kod for s in v.vardiyalar if s.gece_mi}

    # Dönem içi plan ve geçmişle birleşmiş tam plan
    donem_plan: dict[tuple[int, date], list[str]] = defaultdict(list)
    for a in atamalar:
        donem_plan[a["staff_id"], a["work_date"]].append(a["vardiya_kodu"])
    tam_plan: dict[tuple[int, date], list[str]] = defaultdict(list, {k: list(x) for k, x in donem_plan.items()})
    for a in v.gecmis:
        tam_plan[a.personel_id, a.gun].append(a.vardiya_kodu)

    def gece(p_id: int, g: date) -> int:
        return sum(1 for k in tam_plan.get((p_id, g), []) if k in gece_kodlari)

    def gunduz(p_id: int, g: date) -> int:
        return sum(1 for k in tam_plan.get((p_id, g), []) if k not in gece_kodlari)

    def calisiyor(p_id: int, g: date) -> int:
        return len(tam_plan.get((p_id, g), []))

    ilk = v.donem_bas - timedelta(days=GECMIS_GUN)
    tum_gunler = [ilk + timedelta(days=i) for i in range((v.gunler[-1] - ilk).days + 1)]
    # İşlenmiş günler (başka yayından kilitli gelen) yargılanmaz: gerçekleşmiş
    # çizelgedir, solver'ın ürünü değil. Pencere korumaları yalnız KARAR verilen
    # günlere bakar — model.py'deki serbest_donem ile aynı tanım.
    donem = set(v.gunler) - v.islenmis_gunler
    ihlaller: list[Ihlal] = []

    # Merve kuralı: sadece gündüz çalışan birinin O GÜNE ait SADECE_GECE isteği
    # varsa o gün gece çalışabilir (model.py'deki gece_istisnasi ile aynı tanım).
    # Kişinin genel çalışma tipi değişmez, istisna tek güne aittir. Bu istisna
    # kontrolcüde yoksa meşru her gece C-017 ihlali sayılır ve E-10'a kırmızı
    # "çizelge güvenilir değil" satırı düşer.
    gece_istisnasi = {
        (i.personel_id, i.gun)
        for i in v.kesin_istekler + v.tercih_istekler
        if i.tur == "SADECE_GECE"
    }

    # ---------------- A: Adım 2 kuralları ----------------
    for (p_id, g), kodlar in sorted(donem_plan.items(), key=lambda t: (t[0][1], t[0][0])):
        if len(kodlar) > 1:
            ihlaller.append(Ihlal("A-1", "Günde en fazla 1 vardiya", ad[p_id], g,
                                  f"{len(kodlar)} vardiya: {', '.join(kodlar)}"))
        p = kisi[p_id]
        for kod in kodlar:
            gece_mi = kod in gece_kodlari
            if gece_mi and p.uygunluk == "sadece_gunduz" and (p_id, g) not in gece_istisnasi:
                ihlaller.append(Ihlal("A-2", "Çalışma tipi (C-017)", p.ad, g,
                                      f"sadece gündüz çalışabilir, {kod} yazılmış"))
            if not gece_mi and p.uygunluk == "sadece_gece":
                ihlaller.append(Ihlal("A-2", "Çalışma tipi (C-017)", p.ad, g,
                                      f"sadece gece çalışabilir, {kod} yazılmış"))
            if kod == "GUNDUZ_CMT" and (p.rol_kodu != SORUMLU_ROL or g.isoweekday() != 6):
                ihlaller.append(Ihlal("A-5", "Kısa Cumartesi vardiyası", p.ad, g,
                                      "GUNDUZ_CMT yalnız sorumlu hemşireye, yalnız Cumartesi"))

    for y in v.yokluklar:
        if (y.personel_id, y.gun) in donem_plan:
            ihlaller.append(Ihlal("A-3", "İzin / rapor", ad[y.personel_id], y.gun,
                                  f"{y.tur} olduğu gün vardiya yazılmış"))

    for i in v.kesin_istekler:
        kodlar = donem_plan.get((i.personel_id, i.gun), [])
        if not kodlar:
            continue
        gece_var = any(k in gece_kodlari for k in kodlar)
        bozuk = (
            (i.tur == "BOS_GUN")
            or (i.tur == "SADECE_GUNDUZ" and gece_var)
            or (i.tur == "SADECE_GECE" and not gece_var)
        )
        if bozuk:
            ihlaller.append(Ihlal("A-4", "Kesin istek", ad[i.personel_id], i.gun,
                                  f"{i.tur} isteği kesinken {', '.join(kodlar)} yazılmış"))

    # ---------------- B: Adım 3 kuralları ----------------
    n_gece = int(v.kural("C-002").parametreler["max_consecutive_nights"])
    for p in v.personel:
        for i in range(len(tum_gunler) - n_gece):
            pencere = tum_gunler[i:i + n_gece + 1]
            if not any(g in donem for g in pencere):
                continue
            if sum(gece(p.id, g) for g in pencere) > n_gece:
                ihlaller.append(Ihlal("C-002", "Ardışık gece sınırı", p.ad, pencere[-1],
                                      f"{pencere[0]:%d.%m}–{pencere[-1]:%d.%m} arası"
                                      f" {n_gece + 1} gece arka arkaya"))

    n_tetik = int(v.kural("C-014").parametreler["rest_trigger_nights"])
    for p in v.personel:
        for i in range(len(tum_gunler) - n_tetik):
            geceler = tum_gunler[i:i + n_tetik]
            ertesi = tum_gunler[i + n_tetik]
            if ertesi not in donem:
                continue
            if all(gece(p.id, g) for g in geceler) and calisiyor(p.id, ertesi):
                ihlaller.append(Ihlal("C-014", "2 gece sonrası boşluk", p.ad, ertesi,
                                      f"{n_tetik} gece sonrası ({geceler[0]:%d.%m}–"
                                      f"{geceler[-1]:%d.%m}) ertesi gün çalışıyor"))

    for p in v.personel:
        for i in range(len(tum_gunler) - 1):
            g, ertesi = tum_gunler[i], tum_gunler[i + 1]
            if ertesi not in donem:
                continue
            if gece(p.id, g) and gunduz(p.id, ertesi):
                ihlaller.append(Ihlal("C-021", "Gece sonrası gündüz yasağı", p.ad, ertesi,
                                      f"{g:%d.%m} gecesinden sonra gündüz"))

    en_az = int(v.kural("C-016").parametreler["weekly_min_rest_events"])
    bilinen = set(tum_gunler)
    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        if pzt not in haftalar:
            haftalar[pzt] = [pzt + timedelta(days=i) for i in range(7)
                             if (pzt + timedelta(days=i)) in bilinen]
    for pzt, gunler in sorted(haftalar.items()):
        if len(gunler) < C016_ASGARI_BILINEN_GUN or not any(g in donem for g in gunler):
            continue
        tam_hafta = len(gunler) == 7
        for p in v.personel:
            if not tam_hafta and p.sabit_programli:
                continue                                   # dönem sonu yarım hafta muafiyeti
            dolu = sum(1 for g in gunler if calisiyor(p.id, g))
            if dolu > len(gunler) - en_az:
                ihlaller.append(Ihlal("C-016", "Haftada en az 1 boş gün", p.ad, pzt,
                                      f"{gunler[0]:%d.%m}–{gunler[-1]:%d.%m} haftası:"
                                      f" {len(gunler)} günün {dolu}'inde vardiya var"))

    # C-022 acil takviye, C-020'nin bilinçli istisnasıdır. Oryantasyondaki kişinin
    # eşsiz çalıştığı her vakayı _takviye_kontrolu sahipleniyor (meşruysa uyarı,
    # değilse hata). C-020'yi ayrıca yazmak aynı olayı iki kez, üstelik yanlış
    # seviyede raporlardı.
    takviye_bulgulari = _takviye_kontrolu(v, atamalar, kisi, ad)
    takviye_gunleri = {(i.personel, i.gun) for i in takviye_bulgulari}
    ihlaller += takviye_bulgulari

    for o in v.personel:
        if not o.oryantasyonda or o.buddy_id is None:
            continue
        for g in v.gunler:
            if (o.ad, g) in takviye_gunleri:
                continue
            for kod in donem_plan.get((o.id, g), []):
                if kod not in donem_plan.get((o.buddy_id, g), []):
                    ihlaller.append(Ihlal("C-020", "Oryantasyon eşleştirmesi", o.ad, g,
                                          f"{kod} vardiyasında eşi ({ad[o.buddy_id]}) yok"))

    ihlaller += _izin_deseni_kontrolleri(v, calisiyor, donem_plan, ihlal_disi_gunler(v))
    ihlaller += _calisma_suresi_kontrolleri(v, tam_plan, tum_gunler, donem)
    ihlaller += _gorev_kontrolleri(v, atamalar, kisi, ad)

    # İşlenmiş günlerin bulguları düşer; haftalık bulgular zaten yalnız karar
    # verilen günü olan haftalarda üretiliyor.
    ihlaller = [i for i in ihlaller if i.gun is None or i.gun not in v.islenmis_gunler]

    # E-03'te ESNEK yapılmış bir kuralın ihlali model hatası değildir: ceza
    # ödenerek bilerek bozulmuştur. Seviyesi kuralın o anki ayarından gelir.
    esnek = {k.katalog_kodu for k in v.kurallar.values() if k.katalog_kodu and not k.hard_mi}
    return [
        Ihlal(i.kod, i.kural, i.personel, i.gun, i.aciklama, seviye_ustu="gevsek")
        if i.kod in esnek and i.seviye_ustu is None else i
        for i in ihlaller
    ]


def _calisma_suresi_kontrolleri(v: SolverVerisi, tam_plan, tum_gunler: list[date],
                                donem: set[date]) -> list[Ihlal]:
    """C-025 karma hafta · C-026 haftalık 45 sa · C-027 aylık 180 sa · C-028 çalışma günü.

    model.py ile KOD PAYLAŞMAZ (bkz. modül başı): hafta, kişi ve orantı kuralları
    burada yeniden yazıldı. Sayılar veritabanından (seeds/034).
    """
    ihlaller: list[Ihlal] = []
    vardiya = {s.kod: s for s in v.vardiyalar}
    sure: dict[tuple[int, date], int] = {}
    gece_mi: dict[tuple[int, date], bool] = {}
    for a in v.gecmis:
        sure[a.personel_id, a.gun] = a.sure_dk
        gece_mi[a.personel_id, a.gun] = a.gece_mi
    for sa in v.sabit_atamalar:
        sure[sa.personel_id, sa.gun] = sa.sure_dk
        gece_mi[sa.personel_id, sa.gun] = sa.gece_mi
    for (p_id, g), kodlar in tam_plan.items():
        if (p_id, g) not in sure and kodlar and kodlar[0] in vardiya:
            sure[p_id, g] = vardiya[kodlar[0]].sure_dk
            gece_mi[p_id, g] = vardiya[kodlar[0]].gece_mi

    yok = {(y.personel_id, y.gun) for y in v.yokluklar}
    bos = {(i.personel_id, i.gun) for i in v.kesin_istekler if i.tur == "BOS_GUN"}
    kisiler = [p for p in v.personel if not p.sabit_programli and not p.oryantasyonda]
    bilinen = set(v.gunler) | v.gecmis_bilinen_gunler

    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        haftalar.setdefault(pzt, [pzt + timedelta(days=i) for i in range(7)
                                  if pzt + timedelta(days=i) in bilinen])
    haftalar = {pzt: gs for pzt, gs in haftalar.items()
                if len(gs) >= C016_ASGARI_BILINEN_GUN and any(g in donem for g in gs)}

    def sozlesmeli(p, gunler) -> bool:
        return all(g in p.calisabilir_gunler for g in gunler if g in v.gunler)

    son_gun = v.gunler[-1]
    c14 = v.kural("C-014")
    n14 = int(c14.parametreler["rest_trigger_nights"]) if c14 else 0

    def bilinmeyen(gunler) -> tuple[int, int]:
        pzt = gunler[0] - timedelta(days=gunler[0].weekday())
        sonra = sum(1 for i in range(7) if pzt + timedelta(days=i) > son_gun)
        return 7 - len(gunler) - sonra, sonra

    def ertesi_bos(p_id: int) -> int:
        """Ay son n günü gece → gelecek ayın ilk günü C-014 gereği boş."""
        if n14 <= 0:
            return 0
        return int(all(gece_mi.get((p_id, son_gun - timedelta(days=i)), False)
                       for i in range(n14)))

    def etiket(gunler) -> str:
        return f"{gunler[0]:%d.%m}–{gunler[-1]:%d.%m} haftası"

    k25, k26, k27, k28 = (v.kural(c) for c in ("C-025", "C-026", "C-027", "C-028"))
    for pzt, gunler in sorted(haftalar.items()):
        for p in kisiler:
            if not sozlesmeli(p, gunler):
                continue
            calisilan = [g for g in gunler if (p.id, g) in sure]

            if k25 and p.uygunluk == "gunduz_gece" and not any((p.id, g) in yok for g in gunler):
                g_var = any(not gece_mi[p.id, g] for g in calisilan)
                n_var = any(gece_mi[p.id, g] for g in calisilan)
                if calisilan and not (g_var and n_var):
                    ihlaller.append(Ihlal(
                        "C-025", "Karma hafta", p.ad, pzt,
                        f"{etiket(gunler)} {'yalnız gece' if n_var else 'yalnız gündüz'}"
                        f" ({len(calisilan)} vardiya)"))

            once, sonra = bilinmeyen(gunler)
            if k26:
                hedef = int(k26.parametreler["weekly_min_net_hours"] * 60)
                kredi = int(k26.parametreler.get("absence_daily_credit_hours", 0) * 60)
                gun_dk = min((vd.sure_dk for vd in v.vardiyalar if vd.sadece_rol is None),
                             default=0)
                izinli = sum(1 for g in gunler if (p.id, g) in yok)
                # Ay sonu: tam hedef, gelecek günler birer gündüz sayılır (model.py).
                gerek = hedef * (7 - once) // 7 - izinli * kredi - sonra * gun_dk
                net = sum(sure[p.id, g] for g in calisilan)
                if sonra:
                    net -= gun_dk * ertesi_bos(p.id)
                if gerek > 0 and net < gerek:
                    # Kesin izin istekleri haftayı imkânsız kıldıysa solver kuralı
                    # kurmaz (model.py); bu durumda bulgu uyarıdır, model hatası değil.
                    kesinli = any((p.id, g) in bos for g in gunler)
                    ihlaller.append(Ihlal(
                        "C-026", "Haftalık yasal asgari saat", p.ad, pzt,
                        f"{etiket(gunler)}: net {net // 60} sa {net % 60} dk"
                        f" (gereken {gerek // 60} sa {gerek % 60} dk)",
                        seviye_ustu="uyari" if kesinli else None))

            if k28:
                en_az_is = int(k28.parametreler.get("min_weekly_work_days", 0))
                en_fazla_izin = int(k28.parametreler.get("max_weekly_off_days", 7))
                serbest = [g for g in gunler if (p.id, g) not in yok and (p.id, g) not in bos]
                disi = len(gunler) - len(serbest)
                is_gunu = sum(1 for g in serbest if (p.id, g) in sure)
                if sonra:
                    is_gunu -= ertesi_bos(p.id)
                gerek = max(len(serbest) - en_fazla_izin, en_az_is - disi - once - sonra)
                if is_gunu < gerek:
                    ihlaller.append(Ihlal(
                        "C-028", "Haftalık çalışma günü", p.ad, pzt,
                        f"{etiket(gunler)}: {is_gunu} gün çalışma,"
                        f" {len(serbest) - is_gunu} gün izin"))

    bas, son = v.gunler[0], v.gunler[-1]
    if k27 and bas.day == 1 and (son + timedelta(days=1)).day == 1:
        asgari = int(k27.parametreler["monthly_legal_min_net_hours"] * 60)
        c4 = v.kural("C-004")
        dusum = int(c4.parametreler.get("absence_daily_reduction_hours", 0) * 60) if c4 else 0
        for p in v.personel:
            if not p.adalete_girer:
                continue
            izinli = sum(1 for y in v.yokluklar if y.personel_id == p.id)
            gerek = asgari - izinli * dusum
            net = (sum(sure.get((p.id, g), 0) for g in v.gunler)
                   + v.ay_basi_saatler_dk.get(p.id, 0))
            if net < gerek:
                ihlaller.append(Ihlal(
                    "C-027", "Aylık yasal asgari saat", p.ad, None,
                    f"net {net // 60} sa {net % 60} dk (gereken {gerek // 60} sa)"))
    return ihlaller


def ihlal_disi_gunler(v: SolverVerisi) -> set[tuple[int, date]]:
    """İzin/rapor ve KESIN boş gün istekleri. Bu günler izin deseni kurallarının
    DIŞINDA: Edem'in istisnası ("yıllık izin, rapor, kesin off bloğu uzatabilir")."""
    # Yokluk GÜN BAŞINA bir satır (data.py); aralık değil, tek tarih taşır.
    disi = {(y.personel_id, y.gun) for y in v.yokluklar}
    disi |= {(i.personel_id, i.gun) for i in v.kesin_istekler if i.tur == "BOS_GUN"}
    return disi


def _izin_deseni_kontrolleri(v: SolverVerisi, calisiyor, donem_plan,
                             disi: set[tuple[int, date]]) -> list[Ihlal]:
    """C-023 haftalık tam 1 izin · C-024 ardışık izin sınırı · A-6 izin penceresi
    · A-7 sabit haftalık desen.

    Kural metinleri ve sayıları veritabanından gelir (seeds/031); burada yalnız
    sayım yapılıyor.
    """
    ihlaller: list[Ihlal] = []
    donem = set(v.gunler)

    def serbest(p, g: date) -> bool:
        return (p.id, g) not in disi and g in p.calisabilir_gunler

    # Dönemin içinde tamamen kalan Pzt–Paz haftaları
    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        haftalar.setdefault(pzt, [pzt + timedelta(days=i) for i in range(7)])
    tam_haftalar = [gs for gs in haftalar.values() if set(gs) <= donem]

    # ---- C-023: gündüzcü haftada TAM n gün izin ----
    kural = v.kural("C-023")
    if kural is not None:
        adet = int(kural.parametreler["day_only_weekly_off"])
        for gunler in tam_haftalar:
            for p in v.personel:
                if p.uygunluk != "sadece_gunduz":
                    continue
                if not all(serbest(p, g) for g in gunler):
                    continue
                bos = sum(1 for g in gunler if not calisiyor(p.id, g))
                if bos != adet:
                    ihlaller.append(Ihlal(
                        "C-023", "Gündüzcü haftada tam 1 izin", p.ad, gunler[0],
                        f"{gunler[0]:%d.%m}–{gunler[-1]:%d.%m} haftası: {bos} izin günü"
                        f" (olması gereken {adet})"))

    # ---- C-024: ardışık izin sınırı ----
    kural = v.kural("C-024")
    if kural is not None:
        sinir = int(kural.parametreler["max_consecutive_off"])
        for p in v.personel:
            art = 0
            for g in v.gunler:
                if not serbest(p, g):
                    art = 0                      # izinli gün bloğu meşru kılar
                    continue
                art = art + 1 if not calisiyor(p.id, g) else 0
                if art == sinir + 1:
                    ihlaller.append(Ihlal(
                        "C-024", "Ardışık izin sınırı", p.ad, g,
                        f"{sinir + 1} gün üst üste boş ({g - timedelta(days=sinir):%d.%m}"
                        f"–{g:%d.%m})"))

    # ---- A-6: izin günü penceresi (OFF_OLABILIR) ----
    # Yarım haftalar DAHİL (model.py ile aynı kapsam): "hafta içi izin yapma"
    # her gün geçerli. Penceresine uyan serbest günü olmayan hafta atlanır.
    for gunler in haftalar.values():
        for p in v.personel:
            if not p.off_olabilir_gunler:
                continue
            if not any(g.isoweekday() in p.off_olabilir_gunler and serbest(p, g)
                       for g in gunler):
                continue
            for g in gunler:
                if g.isoweekday() in p.off_olabilir_gunler or not serbest(p, g):
                    continue
                if not calisiyor(p.id, g):
                    ihlaller.append(Ihlal(
                        "A-6", "İzin günü penceresi", p.ad, g,
                        "izin günü yalnız "
                        + ", ".join(GUNLER[i - 1] for i in sorted(p.off_olabilir_gunler))
                        + " olabilir"))

    # ---- A-7: sabit haftalık desen ----
    for p in v.personel:
        if not (p.sabit_vardiyalar or p.sabit_off_gunleri):
            continue
        for g in v.gunler:
            if (p.id, g) in disi or g not in p.calisabilir_gunler:
                continue
            isodow = g.isoweekday()
            kodlar = donem_plan.get((p.id, g), [])
            beklenen = p.sabit_vardiyalar.get(isodow)
            if beklenen is not None and kodlar != [beklenen]:
                ihlaller.append(Ihlal("A-7", "Sabit haftalık desen", p.ad, g,
                                      f"{beklenen} bekleniyordu, "
                                      + (", ".join(kodlar) if kodlar else "boş")))
            elif isodow in p.sabit_off_gunleri and kodlar:
                ihlaller.append(Ihlal("A-7", "Sabit haftalık desen", p.ad, g,
                                      f"kesin izin günü ama {', '.join(kodlar)} var"))

    return ihlaller


def _takviye_kontrolu(v: SolverVerisi, atamalar: list[dict], kisi: dict, ad: dict) -> list[Ihlal]:
    """C-022: oryantasyondaki biri EŞİ OLMADAN çalışıyorsa bu acil takviyedir.

    Veritabanında takviyenin ayrı bir izi yok; çizelgeden çıkarıyoruz. Dört
    koşulun HEPSİ doğruysa meşru takviyedir (uyarı); biri bile yanlışsa hatadır
    ve mesaj hangi koşulun tutmadığını söyler.

      a) kişi oryantasyonda
      b) eşi o gün o vardiyada yok
      c) kapsamaya sayılan ekip gerekenin ALTINDA ve oryantasyondakiler
         eklenince gerekeni AŞMIYOR
      d) oryantasyondakinde ambulans rozeti yok VE ambulans çıktıktan sonra
         alanda en az 1 yetkin kişi kalıyor
    """
    kural = v.kural("C-009")
    asgari = int(kural.parametreler.get("min_remaining_triage", 1)) if kural else 1
    gereken = {(s.vardiya_kodu, g): s.min_sayi for s in v.ihtiyaclar
               if s.slot_kodu == "GENEL" for g in s.gunler}

    vardiya: dict[tuple[date, str], list[dict]] = defaultdict(list)
    for a in atamalar:
        vardiya[a["work_date"], a["vardiya_kodu"]].append(a)

    ihlaller: list[Ihlal] = []
    for (g, vardiya_kodu), satirlar in sorted(vardiya.items()):
        n = gereken.get((vardiya_kodu, g))
        if n is None:
            continue
        ekip = sum(1 for a in satirlar if kisi[a["staff_id"]].kapsamaya_sayilir)
        # Ambulanstan sonra alanda kalan yetkin kişi (her iki alan toplamı)
        kalan = sum(
            1 for a in satirlar
            if kisi[a["staff_id"]].kapsamaya_sayilir
            and {"TRIYAJ", "GOZLEM"} & set(a["gorevler"])
            and "AMBULANS" not in set(a["gorevler"])
        )
        takviyeciler = [
            a for a in satirlar
            if kisi[a["staff_id"]].oryantasyonda
            and not any(b["staff_id"] == kisi[a["staff_id"]].buddy_id for b in satirlar)
        ]
        for a in takviyeciler:
            p = kisi[a["staff_id"]]
            eksikler = []
            if ekip >= n:
                eksikler.append(f"(c) ekip zaten yeterli ({ekip}/{n})")
            if ekip + len(takviyeciler) > n:
                eksikler.append(
                    f"(c) takviyeyle gereken aşılıyor ({ekip}+{len(takviyeciler)} > {n})")
            if "AMBULANS" in set(a["gorevler"]):
                eksikler.append("(d) takviyedeyken ambulansa çıkmış")
            if kalan < asgari:
                eksikler.append(f"(d) alanda yetkin kalmıyor ({kalan}/{asgari})")
            if eksikler:
                ihlaller.append(Ihlal(
                    "D-11", "C-022 · geçersiz takviye", p.ad, g,
                    f"{vardiya_kodu}: " + " · ".join(eksikler)))
            else:
                ihlaller.append(Ihlal(
                    "D-11", "C-022 · acil takviye", p.ad, g,
                    f"{vardiya_kodu}: eşi yok, ekip {ekip}/{n} — meşru takviye",
                    seviye_ustu="uyari"))
    return ihlaller


def _gorev_kontrolleri(v: SolverVerisi, atamalar: list[dict], kisi: dict, ad: dict) -> list[Ihlal]:
    """Adım 4: triyaj, gözlem, ambulans, ekip lideri, sayım."""
    ihlaller: list[Ihlal] = []
    yetkinlik = {p.id: p.yetkinlikler for p in v.personel}

    # (gün, vardiya) → o vardiyadaki satırlar
    vardiyalar: dict[tuple[date, str], list[dict]] = defaultdict(list)
    for a in atamalar:
        vardiyalar[a["work_date"], a["vardiya_kodu"]].append(a)

    for a in atamalar:
        gorevler = set(a["gorevler"])
        p = kisi[a["staff_id"]]
        if {"TRIYAJ", "GOZLEM"} <= gorevler:
            ihlaller.append(Ihlal("D-3", "Triyaj ve gözlem ayrıklığı", p.ad, a["work_date"],
                                  "aynı vardiyada hem triyaj hem gözlem"))
        for gorev in gorevler:
            if gorev not in yetkinlik[p.id]:
                # Solver'ın yazdığı rozette yetkinlik eksikse bu bir MODEL HATASI.
                # Elle yapılmış bir düzenlemede ise bilinçli bir istisnadır
                # (örn. oryantasyondaki birinin ambulansa çıkması) — uyarı verilir,
                # engellenmez. Veritabanı trigger'ı da tam bu ayrımı yapıyor.
                elle = a["source"] != "solver"
                ihlaller.append(Ihlal(
                    "D-8", "Rozet yetkinliği", p.ad, a["work_date"],
                    f"{gorev} rozeti var ama yetkinliği yok"
                    + (" (elle yazılmış — bilinçli istisna olabilir)" if elle else ""),
                    seviye_ustu="uyari" if elle else None,
                ))
        # Sorumlu ve oryantasyondakiler bölmenin dışında (seeds/011 ile aynı kural).
        #
        # Kağıttan aktarılan (source='referans') ve HİÇ rozeti olmayan satır
        # "kağıtta görev belirtilmemiş" demektir — kişi o gün triyajda ya da
        # gözlemde olabilir, kağıt söylemiyor. Bunu ihlal saymak, elimizde
        # olmayan bir bilgiyi eksiklik gibi göstermek olurdu. Solver'ın ürettiği
        # satırda (source='solver') aynı durum gerçek bir eksiktir ve sayılır.
        # Yalnız AMBULANS rozeti taşıyan satır da belirsizdir: kağıt ambulansı
        # işaretlemiş ama kişinin triyajda mı gözlemde mi olduğunu yazmamış.
        kagitta_belirtilmemis = (
            a["source"] == "referans" and not (gorevler & {"TRIYAJ", "GOZLEM"})
        )
        if (p.kapsamaya_sayilir and not (gorevler & {"TRIYAJ", "GOZLEM"})
                and not kagitta_belirtilmemis):
            ihlaller.append(Ihlal("D-4", "Rozetsiz çalışan", p.ad, a["work_date"],
                                  f"{a['vardiya_kodu']} vardiyasında ne triyaj ne gözlem"))

    for satir in v.ihtiyaclar:
        istenen = {y.kod for y in satir.yetkinlikler}
        if not istenen:
            continue                                   # GENEL: Adım 2/3'te kontrol edildi
        gorev = next((y.kod for y in satir.yetkinlikler if y.kind == "TASK"), None)
        for g in satir.gunler:
            satirlar = vardiyalar.get((g, satir.vardiya_kodu), [])
            if gorev:
                # Görev satırı: rozeti olan VE satırın tüm yetkinliklerini taşıyan
                sayi = sum(1 for a in satirlar
                           if gorev in a["gorevler"] and istenen <= yetkinlik[a["staff_id"]])
            else:
                # Yetkinlik satırı: rozet yok, o vardiyada bu yetkiye sahip çalışan var mı
                sayi = sum(1 for a in satirlar if istenen <= yetkinlik[a["staff_id"]])
            if sayi < satir.min_sayi:
                kod = {"TRIYAJ": "D-1", "GOZLEM": "D-2", "AMBULANS": "D-5",
                       "SHIFT_YETKILISI": "D-6", "SAYIM": "D-7"}.get(satir.slot_kodu, "D-1")
                ihlaller.append(Ihlal(kod, f"{satir.slot_kodu} asgarisi", "—", g,
                                      f"{satir.vardiya_kodu}: {sayi}/{satir.min_sayi}"))

    # C-009: ambulanstan sonra alanda kalan
    kural = v.kural("C-009")
    if kural:
        for (g, vardiya_kodu), satirlar in sorted(vardiyalar.items()):
            for alan, param in (("TRIYAJ", "min_remaining_triage"),
                                ("GOZLEM", "min_remaining_observation")):
                if param not in kural.parametreler:
                    continue
                asgari = int(kural.parametreler[param])
                kalan = sum(1 for a in satirlar
                            if alan in a["gorevler"] and "AMBULANS" not in a["gorevler"])

                # Kağıttan aktarılan çizelgede, o vardiyada alanı YAZILMAMIŞ ve
                # ambulansa da çıkmamış biri varsa alanın boşaldığını İDDİA EDEMEYİZ:
                # o kişi pekâlâ orada olabilir. Bilmediğimiz bir şeyi ihlal saymak
                # kağıdı olduğundan kötü gösterir (temkinli sayım ilkesi).
                belirsiz = any(
                    a["source"] == "referans"
                    and not (set(a["gorevler"]) & {"TRIYAJ", "GOZLEM"})
                    and "AMBULANS" not in a["gorevler"]
                    and kisi[a["staff_id"]].kapsamaya_sayilir
                    for a in satirlar
                )
                if belirsiz:
                    continue
                # Alanda hiç kimse yoksa bu satır zaten D-1/D-2'de raporlandı
                if any(alan in a["gorevler"] for a in satirlar) and kalan < asgari:
                    ihlaller.append(Ihlal("D-9", "C-009 · ambulans sonrası kalan", "—", g,
                                          f"{vardiya_kodu}: {alan.lower()}ta {kalan}/{asgari}"
                                          " kişi kaldı"))
    return ihlaller


KURAL_SIRASI = ["A-1", "A-2", "A-3", "A-4", "A-5", "A-6", "A-7",
                "C-002", "C-014", "C-021", "C-016", "C-023", "C-024", "C-025",
                "C-026", "C-027", "C-028", "C-020",
                "D-1", "D-2", "D-3", "D-4", "D-5", "D-6", "D-7", "D-8", "D-9", "D-11"]
KURAL_ADI = {
    "A-1": "Günde en fazla 1 vardiya",
    "A-2": "Çalışma tipi — sadece gündüz / sadece gece (C-017)",
    "A-3": "İzin / rapor günü boş",
    "A-4": "Kesin istek (BOS_GUN / SADECE_GUNDUZ / SADECE_GECE)",
    "A-5": "Kısa Cumartesi vardiyası yalnız sorumluya",
    "A-6": "İzin günü penceresi (Cmt/Paz zorunluluğu)",
    "A-7": "Sabit haftalık desen (sorumlunun programı)",
    "C-002": "En fazla 2 gece arka arkaya",
    "C-014": "2 gece sonrası ertesi gün hiç çalışmaz",
    "C-021": "Gece sonrası gündüz yasağı",
    "C-016": "Haftada en az 1 boş gün",
    "C-023": "Gündüzcü haftada TAM 1 gün izin",
    "C-024": "Üst üste en fazla 2 izinsiz boş gün",
    "C-025": "Karma hafta (gündüz+gece personelde tek tip hafta)",
    "C-026": "Haftalık yasal asgari NET saat (45)",
    "C-027": "Aylık yasal asgari NET saat (180)",
    "C-028": "Haftada en az 5 gün çalışma, en fazla 2 izin",
    "C-020": "Oryantasyon eşiyle aynı gün aynı vardiyada",
    "D-1": "C-011 · triyajda en az 3 kişi",
    "D-2": "C-010 · gözlemde en az 2 kişi",
    "D-3": "Triyaj ve gözlem aynı kişide olamaz",
    "D-4": "Vardiyadaki herkes ya triyajda ya gözlemde",
    "D-5": "Ambulans mevcudu (2 kişi)",
    "D-6": "C-007 · vardiyada en az 1 ekip lideri",
    "D-7": "Vardiyada en az 1 sayım yetkilisi",
    "D-8": "Rozet verilen kişide yetkinlik var mı",
    "D-9": "C-009 · ambulans sonrası alanda kalan",
    "D-11": "C-022 · oryantasyon acil takviye",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Kullanım: uv run python -m solver.validate <draft_id>", file=sys.stderr)
        return 2
    draft_id = int(argv[1])
    v = veriyi_oku(draft_id)
    atamalar = atamalari_oku(draft_id)
    ihlaller = kontrol_et(v, atamalar)

    baslik(f"KONTROL — {v.taslak_adi} (#{draft_id})")
    print(f"  Dönem: {tarih(v.donem_bas)} – {tarih(v.gunler[-1])}"
          f"  ·  {len(atamalar)} atama  ·  geçmişten {len(v.gecmis)} atama")

    gruplu: dict[str, list[Ihlal]] = defaultdict(list)
    for i in ihlaller:
        gruplu[i.kod].append(i)

    print()
    for kod in KURAL_SIRASI:
        grup = gruplu.get(kod, [])
        seviyeler = {i.seviye for i in grup}
        isaret = "✓" if not grup else ("✗" if "kati" in seviyeler else "!")
        tip = ("katı" if kod in KATI_KURALLAR else "gevşek") if not grup else \
              ("katı" if "kati" in seviyeler else
               "uyarı" if seviyeler == {"uyari"} else "gevşek")
        ek = "" if not grup else f"{len(grup)} ihlal"
        print(f"  {isaret} {kod:<6} {KURAL_ADI[kod]:<46} {tip:<7} {ek}")
        for i in sorted(grup, key=lambda t: (t.gun or date.min, t.personel))[:12]:
            gun = kisa_tarih(i.gun) if i.gun else "—"
            print(f"        · {i.personel:<16} {gun:<13} {i.aciklama}")
        if len(grup) > 12:
            print(f"        … {len(grup) - 12} ihlal daha")

    print()
    kati = [i for i in ihlaller if i.kati]
    # Hüküm KAYNAĞA göre değişir. Solver ürettiyse katı ihlal modelde hata demektir;
    # elle girilmiş ya da kağıttan aktarılmış çizelgede ise ihlal ÖLÇÜMDÜR — kağıt
    # zaten kuralları bilmiyordu, düzeltilecek bir model yok.
    solverin_mi = any(a.get("source") == "solver" for a in atamalar)
    if kati:
        if solverin_mi:
            print(f"  SONUÇ: {len(kati)} KATI kural ihlali — modelde hata var.")
        else:
            print(f"  SONUÇ: {len(kati)} katı kural ihlali — çizelge elle hazırlanmış,"
                  " ölçüm sonucudur.")
        if len(ihlaller) > len(kati):
            print(f"          Ayrıca {len(ihlaller) - len(kati)} gevşek slot eksiği"
                  " (kadro yetmedi, beklenen).")
    elif ihlaller:
        uyari = [i for i in ihlaller if i.seviye == "uyari"]
        gevsek = len(ihlaller) - len(uyari)
        parca = []
        if gevsek:
            parca.append(f"{gevsek} gevşek slot eksiği (kadro yetmedi)")
        if uyari:
            parca.append(f"{len(uyari)} uyarı (bilinçli istisna)")
        print(f"  SONUÇ: katı ihlal yok. {' · '.join(parca)}.")
    else:
        print("  SONUÇ: temiz — kontrol edilen kuralların hepsi sağlanıyor.")
    print()
    return 1 if kati else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
