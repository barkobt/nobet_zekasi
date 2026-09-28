"""Solver girdisi: bir taslak için gereken her şeyi veritabanından okur.

Bu modül YALNIZCA OKUR. Yazmaz, CP-SAT'ı tanımaz, kural uygulamaz. Amacı, modelin
"veri nereden geliyordu" sorusuyla hiç uğraşmaması: `veriyi_oku(draft_id)` çağrılır,
tek bir donmuş (frozen) nesne döner, model o nesneden okur.

SAAT BİRİMİ — YARIM SAAT (`_yb` son eki)
    CP-SAT yalnızca tam sayılarla çalışır; gündüz 9,5 ve gece 14,5 saat tam sayı değil.
    Her süreyi 2 ile çarpıp tam sayıya çeviriyoruz: gündüz 19, gece 29, sorumlunun kısa
    Cumartesisi 11, aylık 200 saat hedefi 400. Alan adındaki `_yb` bunu hatırlatır;
    19'u yanlışlıkla "19 saat" okumayı engeller.

YETKİNLİK İKİ AYRI ŞEY (migration 010)
    kind='TASK'          → vardiya içinde atanan GÖREV (TRIYAJ, AMBULANS, GOZLEM).
                           Rozeti `assignment_tasks`'ta durur, solver dağıtır.
    kind='QUALIFICATION' → kişinin taşıdığı YETKİ (SAYIM, SHIFT_YETKILISI, HASTA_ILT).
                           `staff_competencies`'te durur, verilidir, dağıtılmaz.
    İkisini karıştırmak migration 010'un düzelttiği hatayı tekrarlamak olur.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from app.settings import get_settings

# Kapsama (GENEL mevcut) sayımından hariç tutulan rol. v_daily_coverage ile aynı
# koşul (migration 009): sorumlu hemşire ve oryantasyondakiler mevcuda sayılmaz.
KAPSAMA_DISI_ROL = "sorumlu_hemsire"

# Bazı vardiya tipleri herkese açık değil. GUNDUZ_CMT, sorumlu hemşirenin kısa
# Cumartesi vardiyasıdır (C-008) ve ihtiyaç şablonunda hiç satırı yoktur.
# Bu kısıt veritabanında SERBEST METİN olarak duruyor (constraints.description),
# makine okunur bir kolonu yok — o yüzden burada, tek bir yerde, adıyla duruyor.
# Şemaya taşınması gerekirse yeni bir migration konusudur.
VARDIYA_KISITLARI: Mapping[str, tuple[str, frozenset[int]]] = {
    # vardiya kodu: (yalnız bu rol, yalnız bu ISO hafta günleri — 6 = Cumartesi)
    "GUNDUZ_CMT": ("sorumlu_hemsire", frozenset({6})),
}


def _yb(saat: Decimal | None) -> int:
    """Saati yarım saat birimine çevirir. Yarım saatin katı değilse hata verir."""
    if saat is None:
        raise ValueError("Süre boş olamaz")
    birim = Decimal(saat) * 2
    if birim != birim.to_integral_value():
        raise ValueError(f"{saat} saat yarım saatin katı değil; modele çevrilemez")
    return int(birim)


# ---------------------------------------------------------------------------
# Veri yapısı
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Personel:
    id: int
    ad: str
    rol_kodu: str
    uygunluk: str                 # gunduz_gece | sadece_gunduz | sadece_gece
    oryantasyonda: bool
    buddy_id: int | None          # oryantasyondaysa eşleştiği eğitim hemşiresi
    yetkinlikler: frozenset[str]
    hedef_saat_yb: int            # HAM hedef; izin düşümü UYGULANMAMIŞ
    hedef_kaynagi: str            # 'sozlesme' | 'kural_varsayilani'
    kapsamaya_sayilir: bool
    kapsama_disi_nedeni: str | None


@dataclass(frozen=True)
class Vardiya:
    id: int
    kod: str
    ad: str
    baslangic: time
    sure_yb: int
    gece_mi: bool                          # crosses_midnight
    sadece_rol: str | None = None          # None = herkese açık
    sadece_hafta_gunleri: frozenset[int] | None = None   # None = her gün

    def secenek_mi(self, rol_kodu: str, isodow: int) -> bool:
        """Bu vardiya, bu rolde biri için bu hafta gününde seçilebilir mi?"""
        if self.sadece_rol is not None and rol_kodu != self.sadece_rol:
            return False
        if self.sadece_hafta_gunleri is not None and isodow not in self.sadece_hafta_gunleri:
            return False
        return True


@dataclass(frozen=True)
class Yokluk:
    """Yıllık izin / rapor: kişi o gün YOK. Hedef saati düşürür (düşüm miktarı Adım 2)."""

    personel_id: int
    gun: date
    tur: str                      # yillik_izin | rapor | ucretsiz_izin | diger


@dataclass(frozen=True)
class Istek:
    """Personel isteği (Orquest'teki "Requests").

    Tür  : BOS_GUN (o gün çalışmasın) · SADECE_GUNDUZ · SADECE_GECE
    Güç  : KESIN    → solver için katı kural
           MUMKUNSE → cezalı tercih; karşılanamazsa raporda görünür
    İzinden farkı: istek 200 saat hedefini DÜŞÜRMEZ (yalnız absences düşürür).
    """

    personel_id: int
    gun: date
    tur: str                      # BOS_GUN | SADECE_GUNDUZ | SADECE_GECE
    durum: str                    # KESIN | MUMKUNSE
    aciklama: str | None


@dataclass(frozen=True)
class IstenenYetkinlik:
    kod: str
    kind: str                     # TASK | QUALIFICATION


@dataclass(frozen=True)
class IhtiyacSatiri:
    satir_id: int
    vardiya_kodu: str
    slot_kodu: str                # GENEL | SHIFT_YETKILISI | SAYIM | TRIYAJ | AMBULANS | GOZLEM
    min_sayi: int
    yetkinlikler: tuple[IstenenYetkinlik, ...]
    kural_kodu: str | None
    katalog_kodu: str | None
    hard_mi: bool                 # kural bağlı değilse hard varsayılır (sözleşme §5)
    agirlik: int | None
    gunler: tuple[date, ...]      # dönem içinde bu satırın geçerli olduğu günler


@dataclass(frozen=True)
class Kural:
    id: int                       # solver_diagnostics.constraint_id için
    kod: str
    katalog_kodu: str | None
    ad: str
    hard_mi: bool
    agirlik: int | None
    kapsam: str                   # kisi | vardiya | gun | hafta | ay
    kaynak: str                   # yasal | kurumsal | tercih | belirsiz
    parametreler: Mapping[str, Decimal]


@dataclass(frozen=True)
class SabitAtama:
    """Dönem İÇİNDE duran ama solver'ın DEĞİŞTİRMEYECEĞİ satır.

    Kural (27.09): yalnız `source='manuel'` (kullanıcı ızgaradan yazdı) ya da
    `is_locked` olan satırlar sabittir. 'solver' ve 'referans' satırları her koşuda
    silinip yeniden üretilir — 'referans' bir başlangıç kopyasıdır, kullanıcı kararı değil.
    """

    personel_id: int
    gun: date
    vardiya_kodu: str
    kaynak: str
    kilitli: bool


@dataclass(frozen=True)
class MevcutAtama:
    """Taslakta ŞU AN duran atama — yalnız CP-SAT'a başlangıç ipucu olarak verilir.

    Kısıt değildir: solver istediği gibi değiştirebilir. Amacı "kopyala → çöz"
    akışında aramanın kaynak çizelgenin yakınından başlaması; böylece sonuç
    kaynaktan kötüye gitmiyor ve koşular arası dalgalanma azalıyor.
    """

    personel_id: int
    gun: date
    vardiya_kodu: str
    gorevler: frozenset[str]


@dataclass(frozen=True)
class GecmisAtama:
    """Dönem başlamadan önceki, DEĞİŞTİRİLEMEZ atama."""

    personel_id: int
    gun: date
    vardiya_kodu: str
    gece_mi: bool
    sure_yb: int
    kaynak: str                   # 'yayinlandi' | 'onceki_ay'


@dataclass(frozen=True)
class SolverVerisi:
    draft_id: int
    taslak_adi: str
    unit_id: int
    donem_bas: date
    donem_bit: date               # DIŞLAYICI üst sınır: bu gün çözülmez
    gunler: tuple[date, ...]
    personel: tuple[Personel, ...]
    vardiyalar: tuple[Vardiya, ...]
    yokluklar: tuple[Yokluk, ...]
    sabit_atamalar: tuple[SabitAtama, ...]
    mevcut_atamalar: tuple[MevcutAtama, ...]   # yalnız ipucu
    kesin_istekler: tuple[Istek, ...]      # KESIN — modele kısıt olarak girer
    tercih_istekler: tuple[Istek, ...]     # MUMKUNSE — cezalı, ihlali raporlanır
    ihtiyaclar: tuple[IhtiyacSatiri, ...]
    kurallar: Mapping[str, Kural]              # constraints.code ile
    uyumsuz_ciftler: tuple[tuple[int, int], ...]
    gecmis: tuple[GecmisAtama, ...]
    ay_basi_saatler_yb: Mapping[int, int]      # personel_id → dönemden önce, AYNI ayda

    def kisi(self, personel_id: int) -> Personel:
        return next(p for p in self.personel if p.id == personel_id)

    def vardiya(self, kod: str) -> Vardiya:
        return next(v for v in self.vardiyalar if v.kod == kod)

    def kural(self, katalog_kodu: str) -> Kural | None:
        """Katalog koduyla (C-002, O-001 …) kural bulur; yoksa None."""
        return next((k for k in self.kurallar.values() if k.katalog_kodu == katalog_kodu), None)


# ---------------------------------------------------------------------------
# Okuma
# ---------------------------------------------------------------------------


def veriyi_oku(draft_id: int) -> SolverVerisi:
    """Taslağı ve solver'ın ihtiyaç duyduğu her şeyi okur. Hiçbir şey yazmaz."""
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            taslak = _taslak(cur, draft_id)
            kurallar = _kurallar(cur)
            kesin, tercih = _istekler(cur, draft_id)
            return SolverVerisi(
                draft_id=draft_id,
                taslak_adi=taslak["name"],
                unit_id=taslak["unit_id"],
                donem_bas=taslak["bas"],
                donem_bit=taslak["bit"],
                gunler=_gunler(cur, draft_id),
                personel=_personel(cur, taslak["bas"], kurallar),
                vardiyalar=_vardiyalar(cur, taslak["unit_id"]),
                yokluklar=_yokluklar(cur, draft_id),
                sabit_atamalar=_sabit_atamalar(cur, draft_id),
                mevcut_atamalar=_mevcut_atamalar(cur, draft_id),
                kesin_istekler=kesin,
                tercih_istekler=tercih,
                ihtiyaclar=_ihtiyaclar(cur, draft_id),
                kurallar=kurallar,
                uyumsuz_ciftler=_uyumsuz_ciftler(cur),
                gecmis=_gecmis(cur, draft_id),
                ay_basi_saatler_yb=_ay_basi_saatler(cur, draft_id),
            )


def _taslak(cur, draft_id: int) -> dict:
    cur.execute(
        """
        SELECT id, unit_id, name, status,
               lower(period) AS bas,      -- dahil
               upper(period) AS bit       -- DIŞLAYICI
        FROM schedule_drafts WHERE id = %s
        """,
        (draft_id,),
    )
    if (satir := cur.fetchone()) is None:
        raise ValueError(f"{draft_id} numaralı taslak yok")
    return satir


def _gunler(cur, draft_id: int) -> tuple[date, ...]:
    # upper(period) DIŞLAYICI olduğu için -1: 21-27 Eylül haftası [09-21, 09-28)
    # olarak durur, 28 Eylül çözülmez (sözleşme §1).
    cur.execute(
        """
        SELECT gs::date AS gun
        FROM schedule_drafts d,
             generate_series(lower(d.period), upper(d.period) - 1, INTERVAL '1 day') gs
        WHERE d.id = %s
        ORDER BY gun
        """,
        (draft_id,),
    )
    return tuple(r["gun"] for r in cur.fetchall())


def _kurallar(cur) -> dict[str, Kural]:
    # constraints'te "açık/kapalı" kolonu YOK: tabloda satırı olan kural açıktır.
    # E-03 kuralı katıdan yumuşağa çevirir (is_hard + default_weight), silmez.
    cur.execute(
        """
        SELECT c.id, c.code, c.catalog_code, c.name, c.is_hard, c.default_weight,
               c.scope, c.source, p.param_key, p.param_value
        FROM constraints c
        LEFT JOIN constraint_params p ON p.constraint_id = c.id
        ORDER BY c.catalog_code NULLS LAST, c.code, p.param_key
        """
    )
    toplanan: dict[str, dict] = {}
    for r in cur.fetchall():
        kayit = toplanan.setdefault(r["code"], {"satir": r, "parametreler": {}})
        if r["param_key"] is not None:
            kayit["parametreler"][r["param_key"]] = r["param_value"]
    return {
        kod: Kural(
            id=k["satir"]["id"],
            kod=kod,
            katalog_kodu=k["satir"]["catalog_code"],
            ad=k["satir"]["name"],
            hard_mi=k["satir"]["is_hard"],
            agirlik=k["satir"]["default_weight"],
            kapsam=k["satir"]["scope"],
            kaynak=k["satir"]["source"],
            parametreler=k["parametreler"],
        )
        for kod, k in toplanan.items()
    }


def _personel(cur, donem_bas: date, kurallar: Mapping[str, Kural]) -> tuple[Personel, ...]:
    # Sözleşme: monthly_target_hours NULL = "kural varsayılanı geçerli".
    # Varsayılan koda YAZILMAZ, constraint_params'tan okunur (bugün 200).
    varsayilan = kurallar["monthly_min_hours"].parametreler["monthly_min_hours"]

    cur.execute(
        """
        SELECT s.id, s.full_name, r.code AS role_code, s.shift_eligibility,
               s.is_orientation, s.buddy_staff_id, ct.monthly_target_hours
        FROM staff s
        JOIN roles r ON r.id = s.role_id
        LEFT JOIN contracts ct ON ct.staff_id = s.id AND ct.valid_period @> %s::date
        WHERE s.is_active
        ORDER BY s.id
        """,
        (donem_bas,),
    )
    satirlar = cur.fetchall()

    cur.execute(
        """
        SELECT sc.staff_id, c.code
        FROM staff_competencies sc
        JOIN competencies c ON c.id = sc.competency_id
        """
    )
    yetkinlik: dict[int, set[str]] = {}
    for r in cur.fetchall():
        yetkinlik.setdefault(r["staff_id"], set()).add(r["code"])

    kisiler = []
    for r in satirlar:
        if r["is_orientation"]:
            neden = "oryantasyonda"
        elif r["role_code"] == KAPSAMA_DISI_ROL:
            neden = "sorumlu hemşire"
        else:
            neden = None
        hedef = r["monthly_target_hours"]
        kisiler.append(
            Personel(
                id=r["id"],
                ad=r["full_name"],
                rol_kodu=r["role_code"],
                uygunluk=r["shift_eligibility"],
                oryantasyonda=r["is_orientation"],
                buddy_id=r["buddy_staff_id"],
                yetkinlikler=frozenset(yetkinlik.get(r["id"], ())),
                hedef_saat_yb=_yb(hedef if hedef is not None else varsayilan),
                hedef_kaynagi="sozlesme" if hedef is not None else "kural_varsayilani",
                kapsamaya_sayilir=neden is None,
                kapsama_disi_nedeni=neden,
            )
        )
    return tuple(kisiler)


def _vardiyalar(cur, unit_id: int) -> tuple[Vardiya, ...]:
    # is_active = FALSE olanlar (24 saatlik vardiyalar, C-018) dışarıda kalır.
    cur.execute(
        """
        SELECT id, code, name, start_time, duration_hours, crosses_midnight
        FROM shift_types
        WHERE unit_id = %s AND is_active
        ORDER BY start_time, duration_hours
        """,
        (unit_id,),
    )
    vardiyalar = []
    for r in cur.fetchall():
        rol, gunler = VARDIYA_KISITLARI.get(r["code"], (None, None))
        vardiyalar.append(
            Vardiya(
                id=r["id"],
                kod=r["code"],
                ad=r["name"],
                baslangic=r["start_time"],
                sure_yb=_yb(r["duration_hours"]),
                gece_mi=r["crosses_midnight"],
                sadece_rol=rol,
                sadece_hafta_gunleri=gunler,
            )
        )
    return tuple(vardiyalar)


def _yokluklar(cur, draft_id: int) -> tuple[Yokluk, ...]:
    # absences.period bir aralıktır; modelin ihtiyacı GÜN listesi. Kesişimi günlere açıyoruz.
    cur.execute(
        """
        SELECT ab.staff_id, gs::date AS gun, ab.absence_type
        FROM schedule_drafts d
        JOIN absences ab ON ab.period && d.period
        CROSS JOIN LATERAL generate_series(
                 GREATEST(lower(ab.period), lower(d.period)),
                 LEAST(upper(ab.period), upper(d.period)) - 1,
                 INTERVAL '1 day') gs
        WHERE d.id = %s
        ORDER BY ab.staff_id, gun
        """,
        (draft_id,),
    )
    return tuple(
        Yokluk(personel_id=r["staff_id"], gun=r["gun"], tur=r["absence_type"])
        for r in cur.fetchall()
    )


# Eski sözlükten yeni sözlüğe eşleme. 'off_talebi' ile BOS_GUN aynı şeydir
# ("o gün çalışmasın"), yalnız adı değişti. Açılış/kapanış tercihinin yeni modelde
# karşılığı YOK; olduğu gibi bırakılır ve inspect bunları uyarı olarak listeler —
# sessizce düşürmüyoruz.
ISTEK_TURU_ESLEME: Mapping[str, str] = {"off_talebi": "BOS_GUN"}

ISTEK_TURLERI = ("BOS_GUN", "SADECE_GUNDUZ", "SADECE_GECE")


def _sabit_atamalar(cur, draft_id: int) -> tuple[SabitAtama, ...]:
    """Dönem içindeki dokunulmaz satırlar: elle yazılmış ya da kilitlenmiş olanlar."""
    cur.execute(
        """
        SELECT a.staff_id, a.work_date, st.code AS vardiya_kodu, a.source, a.is_locked
        FROM assignments a
        JOIN schedule_drafts d ON d.id = a.draft_id
        JOIN shift_types st    ON st.id = a.shift_type_id
        WHERE a.draft_id = %s
          AND d.period @> a.work_date
          AND (a.source = 'manuel' OR a.is_locked)
        ORDER BY a.work_date, a.staff_id
        """,
        (draft_id,),
    )
    return tuple(
        SabitAtama(
            personel_id=r["staff_id"],
            gun=r["work_date"],
            vardiya_kodu=r["vardiya_kodu"],
            kaynak=r["source"],
            kilitli=r["is_locked"],
        )
        for r in cur.fetchall()
    )


def _mevcut_atamalar(cur, draft_id: int) -> tuple[MevcutAtama, ...]:
    """Taslaktaki tüm dönem içi atamalar ve görev rozetleri (ipucu için)."""
    cur.execute(
        """
        SELECT a.staff_id, a.work_date, st.code AS vardiya_kodu,
               coalesce(array_agg(c.code) FILTER (WHERE c.code IS NOT NULL), '{}') AS gorevler
        FROM assignments a
        JOIN schedule_drafts d ON d.id = a.draft_id
        JOIN shift_types st    ON st.id = a.shift_type_id
        LEFT JOIN assignment_tasks t ON t.assignment_id = a.id
        LEFT JOIN competencies c     ON c.id = t.competency_id
        WHERE a.draft_id = %s AND d.period @> a.work_date
        GROUP BY a.staff_id, a.work_date, st.code
        """,
        (draft_id,),
    )
    return tuple(
        MevcutAtama(
            personel_id=r["staff_id"], gun=r["work_date"],
            vardiya_kodu=r["vardiya_kodu"], gorevler=frozenset(r["gorevler"]),
        )
        for r in cur.fetchall()
    )


def _istekler(cur, draft_id: int) -> tuple[tuple[Istek, ...], tuple[Istek, ...]]:
    """İstekleri gücüne göre ayırır: KESIN = katı kural, MUMKUNSE = cezalı tercih."""
    cur.execute(
        """
        SELECT ar.staff_id, ar.target_date, ar.rule_type, ar.status AS durum, ar.note
        FROM schedule_drafts d
        JOIN availability_rules ar ON d.period @> ar.target_date
        WHERE d.id = %s
        ORDER BY ar.staff_id, ar.target_date
        """,
        (draft_id,),
    )
    istekler = [
        Istek(
            personel_id=r["staff_id"],
            gun=r["target_date"],
            tur=ISTEK_TURU_ESLEME.get(r["rule_type"], r["rule_type"]),
            durum=r["durum"],
            aciklama=r["note"],
        )
        for r in cur.fetchall()
    ]
    kesin = tuple(i for i in istekler if i.durum == "KESIN")
    tercih = tuple(i for i in istekler if i.durum != "KESIN")
    return kesin, tercih


def _ihtiyaclar(cur, draft_id: int) -> tuple[IhtiyacSatiri, ...]:
    # Şablon dönem ortasında değişebilir (need_periods). Bu yüzden satırı "hangi
    # günlerde geçerli" listesiyle birlikte okuyoruz: aynı satır, kendi gün kümesiyle.
    cur.execute(
        """
        WITH gunler AS (
            SELECT d.unit_id, gs::date AS gun
            FROM schedule_drafts d,
                 generate_series(lower(d.period), upper(d.period) - 1, INTERVAL '1 day') gs
            WHERE d.id = %s
        )
        SELECT ntr.id AS satir_id, st.code AS vardiya_kodu, ntr.slot_code, ntr.min_count,
               c.code AS kural_kodu, c.catalog_code, c.is_hard, c.default_weight,
               array_agg(g.gun ORDER BY g.gun) AS gunler
        FROM gunler g
        JOIN need_periods np        ON np.unit_id = g.unit_id AND np.valid_period @> g.gun
        JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
        JOIN shift_types st         ON st.id = ntr.shift_type_id
        LEFT JOIN constraints c     ON c.id = ntr.constraint_id
        GROUP BY ntr.id, st.code, st.start_time, ntr.slot_code, ntr.min_count,
                 c.code, c.catalog_code, c.is_hard, c.default_weight
        ORDER BY st.start_time, ntr.slot_code
        """,
        (draft_id,),
    )
    satirlar = cur.fetchall()

    cur.execute(
        """
        SELECT x.need_template_row_id AS satir_id, c.code, c.kind
        FROM need_template_row_competencies x
        JOIN competencies c ON c.id = x.competency_id
        ORDER BY c.code
        """
    )
    istenen: dict[int, list[IstenenYetkinlik]] = {}
    for r in cur.fetchall():
        istenen.setdefault(r["satir_id"], []).append(
            IstenenYetkinlik(kod=r["code"], kind=r["kind"])
        )

    return tuple(
        IhtiyacSatiri(
            satir_id=r["satir_id"],
            vardiya_kodu=r["vardiya_kodu"],
            slot_kodu=r["slot_code"],
            min_sayi=r["min_count"],
            yetkinlikler=tuple(istenen.get(r["satir_id"], ())),
            kural_kodu=r["kural_kodu"],
            katalog_kodu=r["catalog_code"],
            # Kural bağlı değilse hard kabul edilir (sözleşme §5: NULL = hard, ağırlıksız)
            hard_mi=True if r["is_hard"] is None else r["is_hard"],
            agirlik=r["default_weight"],
            gunler=tuple(r["gunler"]),
        )
        for r in satirlar
    )


def _uyumsuz_ciftler(cur) -> tuple[tuple[int, int], ...]:
    cur.execute(
        "SELECT staff_id_low, staff_id_high FROM staff_conflicts ORDER BY 1, 2"
    )
    return tuple((r["staff_id_low"], r["staff_id_high"]) for r in cur.fetchall())


def _gecmis_pencere(cur, draft_id: int) -> list[dict]:
    """Dönemden ÖNCEKİ değiştirilemez atamalar, tek sorguda.

    Pencere: (dönem başı − 7 gün) ile ayın 1'inden hangisi daha eriyse oradan başlar,
    dönem başında biter. İki kaynak var ve aynı kişi-gün ikisinde de olabilir:
      1) aynı taslakta, dönemin dışında duran bağlam satırları (sözleşme §2)
      2) aynı birimin YAYINLANMIŞ taslaklarındaki gerçek günler
    Çakışırsa yayınlanmış çizelge esastır (DISTINCT ON + sıralama bunu yapıyor).
    """
    cur.execute(
        """
        WITH d AS (
            SELECT id, unit_id, lower(period) AS bas FROM schedule_drafts WHERE id = %s
        ),
        pencere AS (
            SELECT LEAST(bas - 7, date_trunc('month', bas)::date) AS bas, bas AS bit FROM d
        ),
        ham AS (
            -- 1) Aynı taslağın bağlam satırları
            SELECT a.staff_id, a.work_date, st.code AS vardiya_kodu,
                   st.crosses_midnight, st.duration_hours, 'onceki_ay' AS kaynak
            FROM assignments a
            JOIN shift_types st ON st.id = a.shift_type_id
            JOIN d ON d.id = a.draft_id
            JOIN pencere p ON a.work_date >= p.bas AND a.work_date < p.bit

            UNION ALL

            -- 2) Yayınlanmış başka taslakların KENDİ dönemine düşen günleri
            SELECT a.staff_id, a.work_date, st.code,
                   st.crosses_midnight, st.duration_hours, 'yayinlandi'
            FROM assignments a
            JOIN schedule_drafts y ON y.id = a.draft_id
                                  AND y.status = 'yayinlandi'
                                  AND y.period @> a.work_date
            JOIN shift_types st ON st.id = a.shift_type_id
            JOIN d ON y.unit_id = d.unit_id AND y.id <> d.id
            JOIN pencere p ON a.work_date >= p.bas AND a.work_date < p.bit
        )
        SELECT DISTINCT ON (staff_id, work_date)
               staff_id, work_date, vardiya_kodu, crosses_midnight, duration_hours, kaynak
        FROM ham
        ORDER BY staff_id, work_date,
                 CASE kaynak WHEN 'yayinlandi' THEN 0 ELSE 1 END
        """,
        (draft_id,),
    )
    return cur.fetchall()


def _gecmis(cur, draft_id: int) -> tuple[GecmisAtama, ...]:
    """Ardışık gece (C-002), 2 gece sonrası boşluk (C-014) ve haftalık dinlenme
    (C-016) kuralları geriye bakar. Pratikte son 7 gün yeterli."""
    cur.execute(
        "SELECT lower(period) - 7 AS esik FROM schedule_drafts WHERE id = %s", (draft_id,)
    )
    esik = cur.fetchone()["esik"]
    return tuple(
        GecmisAtama(
            personel_id=r["staff_id"],
            gun=r["work_date"],
            vardiya_kodu=r["vardiya_kodu"],
            gece_mi=r["crosses_midnight"],
            sure_yb=_yb(r["duration_hours"]),
            kaynak=r["kaynak"],
        )
        for r in _gecmis_pencere(cur, draft_id)
        if r["work_date"] >= esik
    )


def _ay_basi_saatler(cur, draft_id: int) -> dict[int, int]:
    """Dönem ayın ortasından başlıyorsa, aynı ayın önceki günlerinde çalışılmış saat.

    Aylık hedef (C-004) ay bazlıdır; dönem ayın 12'sinde başlıyorsa 1-11 arasında
    çalışılmış saatler hedeften düşülmüş sayılmalı. Dönem ayın 1'inde başlıyorsa boş döner.
    """
    cur.execute(
        "SELECT date_trunc('month', lower(period))::date AS ay_basi FROM schedule_drafts WHERE id = %s",
        (draft_id,),
    )
    ay_basi = cur.fetchone()["ay_basi"]
    toplam: dict[int, int] = {}
    for r in _gecmis_pencere(cur, draft_id):
        if r["work_date"] >= ay_basi:
            toplam[r["staff_id"]] = toplam.get(r["staff_id"], 0) + _yb(r["duration_hours"])
    return toplam
