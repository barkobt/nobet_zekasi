"""E-08 taslaklar ve solver koşuları — düz SQL."""

from datetime import date

from app.db import cursor

# Taslak listesi + metrikler. Alt sorgular LATERAL yerine skaler: satır sayısı az
# (ayda birkaç taslak), okunabilirlik ağır basıyor.
_LISTE = """
SELECT d.id, d.name, d.status, d.created_at, d.published_at,
       lower(d.period) AS period_start, upper(d.period) AS period_end,
       u.name AS unit_name,
       -- Son güncellenme: taslakta ayrı bir updated_at kolonu yok, en son NE
       -- olduğuna bakıyoruz — yayınlanma, son çözüm koşusu, son atama yazımı.
       GREATEST(
           d.created_at,
           COALESCE(d.published_at, d.created_at),
           COALESCE((SELECT max(r.started_at) FROM solver_runs r WHERE r.draft_id = d.id),
                    d.created_at),
           COALESCE((SELECT max(a.created_at) FROM assignments a WHERE a.draft_id = d.id),
                    d.created_at)
       ) AS updated_at,
       (SELECT count(*) FROM assignments a WHERE a.draft_id = d.id)               AS assignment_count,
       (SELECT count(DISTINCT a.staff_id) FROM assignments a WHERE a.draft_id = d.id) AS staff_count,
       -- Eksik slot YALNIZCA atama bulunan günlerde sayılır. Aksi halde kısmi bir
       -- taslakta ayın geri kalan boş günleri de "eksik" görünür ve sayı anlamsızlaşır
       -- (referans hafta: 21 yerine 285 çıkıyordu).
       (SELECT count(*) FROM v_daily_coverage c
         WHERE c.draft_id = d.id AND c.assigned < c.required
           AND EXISTS (SELECT 1 FROM assignments a
                        WHERE a.draft_id = d.id AND a.work_date = c.day))         AS shortfall_count,
       (SELECT min(a.work_date) FROM assignments a WHERE a.draft_id = d.id)       AS ilk_gun,
       (SELECT max(a.work_date) FROM assignments a WHERE a.draft_id = d.id)       AS son_gun,
       COALESCE((SELECT sum(h.planned_hours) FROM v_assignment_hours h
                  WHERE h.draft_id = d.id), 0)                                    AS total_hours,
       COALESCE((SELECT sum(m.overtime_max) FROM v_monthly_hours m
                  WHERE m.draft_id = d.id), 0)                                    AS overtime_hours,
       -- Adalet farkı YALNIZ adalet havuzundan (sorumlu, oryantasyon ve dönemin
       -- tamamında sözleşmesi olmayanlar hariç). Havuz dışını katmak farkı yanlış
       -- büyütüyor; ölçüt solver/data.py → Personel.adalete_girer ile aynı.
       COALESCE((SELECT max(m.worked_hours) - min(m.worked_hours)
                   FROM v_monthly_hours m
                   JOIN staff st ON st.id = m.staff_id
                   JOIN roles rl ON rl.id = st.role_id
                  WHERE m.draft_id = d.id AND m.worked_hours > 0
                    AND NOT st.is_orientation
                    AND rl.code <> 'sorumlu_hemsire'
                    AND EXISTS (SELECT 1 FROM contracts ct
                                 WHERE ct.staff_id = st.id
                                   AND ct.valid_period @> d.period)), 0)          AS fairness_gap
FROM schedule_drafts d
JOIN units u ON u.id = d.unit_id
"""

# Koşu + o koşunun ürettiği sayılar. params_snapshot'tan yalnızca 'solver' anahtarı
# okunuyor: arayüzün dürüstlük etiketi buna bakıyor (şemaya kolon eklemeye gerek yok).
_KOSU = """
SELECT r.id, r.draft_id, r.status, r.started_at, r.finished_at,
       r.time_limit_seconds, r.objective_value,
       (r.params_snapshot ->> 'solver') AS solver_impl,
       (SELECT count(*) FROM assignments a
         WHERE a.draft_id = r.draft_id AND a.source = 'solver')  AS assignment_count,
       (SELECT count(*) FROM solver_diagnostics g
         WHERE g.solver_run_id = r.id)                           AS diagnostic_count,
       EXTRACT(EPOCH FROM (COALESCE(r.finished_at, CURRENT_TIMESTAMP) - r.started_at)) AS elapsed_s
FROM solver_runs r
"""


async def listele() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_LISTE + " ORDER BY lower(d.period) DESC, d.id DESC")
        return await cur.fetchall()


async def getir(draft_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_LISTE + " WHERE d.id = %s", (draft_id,))
        return await cur.fetchone()


async def olustur(unit_code: str, period_start: date, period_end: date, name: str) -> dict:
    """period_end DIŞLAYICIdır: [başlangıç, bitiş). Router kullanıcının seçtiği
    kapsayıcı bitiş gününe 1 ekleyerek çağırır."""
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO schedule_drafts (unit_id, period, name)
               SELECT id, daterange(%s, %s, '[)'), %s FROM units WHERE code = %s
               RETURNING id""",
            (period_start, period_end, name, unit_code),
        )
        return await cur.fetchone()


async def kosu_ac(draft_id: int, time_limit_s: int) -> int:
    """solver_runs satırını 'CALISIYOR' ile açar.

    Router açar, run_solver sonuçlandırır (bkz. solver/interface.py). Böylece
    frontend POST'un yanıtında hemen yoklayacak bir run_id'ye sahip olur.
    """
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO solver_runs (draft_id, status, time_limit_seconds)
               VALUES (%s, 'CALISIYOR', %s) RETURNING id""",
            (draft_id, time_limit_s),
        )
        return (await cur.fetchone())["id"]


# Bir koşu, süre limitinin bu katı kadar zamandır 'CALISIYOR' duruyorsa ÖLMÜŞ
# sayılır. Sebep: arka plan görevi süreçle birlikte ölür (deploy, çökme, yeniden
# başlatma) ama satır 'CALISIYOR' kalır — ve çift tıklama koruması o ölü satırı
# bulup döndürdüğü için taslak bir daha HİÇ çözülemezdi.
OLU_KOSU_KATSAYISI = 3


async def olu_kosulari_kapat() -> int:
    """Süresini fazlasıyla aşmış 'CALISIYOR' satırları HATA'ya çeker.

    Zaman aşımı koşunun kendi time_limit_seconds'ından türer: 60 sn limitli bir
    koşu 3 dakikadır sürüyorsa süreç ölmüş demektir.
    """
    async with cursor() as cur:
        await cur.execute(
            """
            UPDATE solver_runs
               SET status = 'HATA', finished_at = CURRENT_TIMESTAMP
             WHERE status = 'CALISIYOR'
               AND started_at < CURRENT_TIMESTAMP
                   - (COALESCE(time_limit_seconds, 60) * %s) * INTERVAL '1 second'
            RETURNING id
            """,
            (OLU_KOSU_KATSAYISI,),
        )
        return len(await cur.fetchall())


async def calisan_kosu(draft_id: int) -> dict | None:
    """Aynı taslak için zaten süren bir koşu var mı? (çift tıklama koruması)"""
    await olu_kosulari_kapat()
    async with cursor() as cur:
        await cur.execute(
            _KOSU + " WHERE r.draft_id = %s AND r.status = 'CALISIYOR' ORDER BY r.started_at DESC LIMIT 1",
            (draft_id,),
        )
        return await cur.fetchone()


async def suren_kosu_sayisi() -> int:
    """Şu an kaç taslak çözülüyor (ölüler ayıklandıktan sonra)."""
    await olu_kosulari_kapat()
    async with cursor() as cur:
        await cur.execute("SELECT count(*) AS adet FROM solver_runs WHERE status = 'CALISIYOR'")
        return (await cur.fetchone())["adet"]


async def kosu(run_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_KOSU + " WHERE r.id = %s", (run_id,))
        return await cur.fetchone()


async def kosular(draft_id: int) -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_KOSU + " WHERE r.draft_id = %s ORDER BY r.started_at DESC", (draft_id,))
        return await cur.fetchall()


async def son_kosu(draft_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            _KOSU + " WHERE r.draft_id = %s ORDER BY r.started_at DESC LIMIT 1", (draft_id,)
        )
        return await cur.fetchone()


_TESHIS = """
SELECT g.id, g.severity, g.work_date, g.message, g.suggestion,
       c.code AS constraint_code, c.catalog_code, c.name AS constraint_name,
       s.full_name AS staff_name
FROM solver_diagnostics g
LEFT JOIN constraints c ON c.id = g.constraint_id
LEFT JOIN staff s       ON s.id = g.staff_id
WHERE g.solver_run_id = %s
ORDER BY g.work_date NULLS FIRST, g.id
"""


async def teshisler(run_id: int) -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_TESHIS, (run_id,))
        return await cur.fetchall()


# Başlangıç verisi: yeni taslağı boş bırakmak yerine mevcut bir çizelgeden doldur.
# Kopyalanan satırlar source='referans' olur — solver onları silmez (yalnız kendi
# ürettiği 'solver' satırlarını siler), ama "elle yapılmış değişiklik" de SAYILMAZ;
# kullanıcı bunlara dokunmadı (migration 013). lock_seeded ayrıca is_locked yazar.
_KOPYALA = """
WITH hedef AS (
    SELECT id AS draft_id, period FROM schedule_drafts WHERE id = %(draft_id)s
),
kaynak AS (
    SELECT a.staff_id, a.shift_type_id, a.work_date, a.id AS kaynak_id,
           EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
    FROM assignments a
    JOIN schedule_drafts d ON d.id = a.draft_id
    WHERE d.id = %(kaynak_id)s
),
gunler AS (
    SELECT h.draft_id, gs::date AS gun
    FROM hedef h, generate_series(lower(h.period), upper(h.period) - 1, INTERVAL '1 day') gs
),
eslesme AS (
    -- Hafta gününe göre döşe: kaynak 1 hafta, hedef herhangi bir uzunlukta olabilir.
    SELECT g.draft_id, k.staff_id, k.shift_type_id, g.gun AS work_date, k.kaynak_id
    FROM gunler g
    JOIN kaynak k ON k.hafta_gunu = EXTRACT(ISODOW FROM g.gun)::int
)
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source, is_locked)
SELECT draft_id, staff_id, shift_type_id, work_date, 'referans', %(kilitle)s
FROM eslesme
ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING
RETURNING id, staff_id, work_date
"""

_ROZET_KOPYALA = """
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT y.id, t.competency_id
FROM assignments y
JOIN assignments k ON k.draft_id = %(kaynak_id)s
                 AND k.staff_id = y.staff_id
                 AND EXTRACT(ISODOW FROM k.work_date) = EXTRACT(ISODOW FROM y.work_date)
JOIN assignment_tasks t ON t.assignment_id = k.id
WHERE y.draft_id = %(draft_id)s
  -- Yetkinliği olmayana görev kopyalama: trigger zaten reddederdi.
  AND EXISTS (SELECT 1 FROM staff_competencies sc
              WHERE sc.staff_id = y.staff_id AND sc.competency_id = t.competency_id)
ON CONFLICT DO NOTHING
"""


async def kaynak_taslak_bul(tur: str, period_start: date, period_end: date) -> int | None:
    """Hangi taslaktan kopyalanacak?

    'referans'    → elle hazırlanan referans hafta
    'yayinlanmis' → aynı aralıkla çakışan yayınlanmış çizelge (en yenisi)
    """
    async with cursor() as cur:
        if tur == "referans":
            await cur.execute(
                "SELECT id FROM schedule_drafts WHERE name LIKE 'Referans:%' ORDER BY id LIMIT 1"
            )
        elif tur == "yayinlanmis":
            await cur.execute(
                """SELECT id FROM schedule_drafts
                    WHERE status = 'yayinlandi' AND period && daterange(%s, %s, '[)')
                    ORDER BY lower(period) DESC LIMIT 1""",
                (period_start, period_end),
            )
        else:
            return None
        satir = await cur.fetchone()
        return satir["id"] if satir else None


async def baslangic_verisi_kopyala(draft_id: int, kaynak_id: int, kilitle: bool) -> int:
    p = {"draft_id": draft_id, "kaynak_id": kaynak_id, "kilitle": kilitle}
    async with cursor() as cur:
        await cur.execute(_KOPYALA, p)
        sayi = cur.rowcount
        await cur.execute(_ROZET_KOPYALA, {"draft_id": draft_id, "kaynak_id": kaynak_id})
    return sayi


async def durum(draft_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """SELECT status, (SELECT count(*) FROM assignments a WHERE a.draft_id = d.id) AS atama
               FROM schedule_drafts d WHERE d.id = %s""",
            (draft_id,),
        )
        return await cur.fetchone()


async def sil(draft_id: int) -> dict | None:
    """Taslak silinince atamaları, koşuları ve teşhisleri de gider (ON DELETE CASCADE)."""
    async with cursor() as cur:
        await cur.execute("DELETE FROM schedule_drafts WHERE id = %s RETURNING id", (draft_id,))
        return await cur.fetchone()


_CAKISANLAR = """
SELECT d.id, d.name, d.period,
       -- YALNIZCA kullanıcının ızgara hücresinden yaptığı düzenlemeler.
       -- Kopyalananlar 'referans' olduğu için buraya girmiyor (migration 013).
       (SELECT count(*) FROM assignments a
         WHERE a.draft_id = d.id AND a.source = 'manuel') AS elle_degisiklik,
       -- Eskinin YENİ taslağın dışında kalan kısmı
       (SELECT d.period - y.period FROM schedule_drafts y WHERE y.id = %(yeni)s) AS disarida
FROM schedule_drafts d
WHERE d.status = 'yayinlandi'
  AND d.id <> %(yeni)s
  AND d.unit_id = (SELECT unit_id FROM schedule_drafts WHERE id = %(yeni)s)
  AND d.period && (SELECT period FROM schedule_drafts WHERE id = %(yeni)s)
ORDER BY lower(d.period)
"""


async def cakisan_yayinlar(draft_id: int) -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_CAKISANLAR, {"yeni": draft_id})
        return await cur.fetchall()


async def yayinla(draft_id: int) -> dict | None:
    """Çakışan yayınlanmış çizelgeleri ARŞİVE alır, sonra bunu yayınlar.

    İkisi TEK transaction: arşivleme yapılıp yayınlama başarısız olursa birim
    yayınlanmış çizelgesiz kalırdı. EXCLUDE kısıtı (ex_drafts_one_published)
    yalnız status='yayinlandi' satırlara baktığı için önce arşivleyip sonra
    yayınlamak kısıtı ihlal etmiyor.

    Silmiyoruz: arşivdeki çizelge açılıp tekrar uygulanabilir — geri dönüş yolu bu.
    """
    async with cursor() as cur:
        await cur.execute(
            """UPDATE schedule_drafts d
                  SET status = 'arsiv'
                WHERE d.status = 'yayinlandi'
                  AND d.id <> %(yeni)s
                  AND d.unit_id = (SELECT unit_id FROM schedule_drafts WHERE id = %(yeni)s)
                  AND d.period && (SELECT period FROM schedule_drafts WHERE id = %(yeni)s)""",
            {"yeni": draft_id},
        )
        await cur.execute(
            """UPDATE schedule_drafts
                  SET status = 'yayinlandi',
                      published_at = COALESCE(published_at, CURRENT_TIMESTAMP)
                WHERE id = %s RETURNING id""",
            (draft_id,),
        )
        return await cur.fetchone()


async def ad_degistir(draft_id: int, yeni_ad: str) -> dict | None:
    """Taslağın adı kullanıcı verisidir; değiştirilebilmesi gerekir."""
    async with cursor() as cur:
        await cur.execute(
            "UPDATE schedule_drafts SET name = %s WHERE id = %s RETURNING id",
            (yeni_ad, draft_id),
        )
        return await cur.fetchone()


async def kopyala(draft_id: int, yeni_ad: str) -> dict | None:
    """Aynı dönem, aynı atamalar, yeni taslak. Koşu geçmişi kopyalanmaz —
    kopya henüz çözülmemiştir; atamalar 'referans' olarak taşınır."""
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO schedule_drafts (unit_id, period, name)
               SELECT unit_id, period, %s FROM schedule_drafts WHERE id = %s
               RETURNING id""",
            (yeni_ad, draft_id),
        )
        if (yeni := await cur.fetchone()) is None:
            return None

        await cur.execute(
            """INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date,
                                        source, is_locked)
               SELECT %s, staff_id, shift_type_id, work_date, 'referans', is_locked
               FROM assignments WHERE draft_id = %s""",
            (yeni["id"], draft_id),
        )
        await cur.execute(
            """INSERT INTO assignment_tasks (assignment_id, competency_id)
               SELECT y.id, t.competency_id
               FROM assignments y
               JOIN assignments k ON k.draft_id = %s AND k.staff_id = y.staff_id
                                 AND k.work_date = y.work_date
               JOIN assignment_tasks t ON t.assignment_id = k.id
               WHERE y.draft_id = %s
               ON CONFLICT DO NOTHING""",
            (draft_id, yeni["id"]),
        )
        return yeni
