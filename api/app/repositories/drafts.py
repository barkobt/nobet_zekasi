"""E-08 taslaklar ve solver koşuları — düz SQL."""

from datetime import date

from app.db import cursor

# Taslak listesi + metrikler. Alt sorgular LATERAL yerine skaler: satır sayısı az
# (ayda birkaç taslak), okunabilirlik ağır basıyor.
_LISTE = """
SELECT d.id, d.name, d.month_start, d.status, d.created_at, d.published_at,
       u.name AS unit_name,
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
       COALESCE((SELECT max(m.worked_hours) - min(m.worked_hours) FROM v_monthly_hours m
                  WHERE m.draft_id = d.id AND m.worked_hours > 0), 0)             AS fairness_gap
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
        await cur.execute(_LISTE + " ORDER BY d.month_start DESC, d.id DESC")
        return await cur.fetchall()


async def getir(draft_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_LISTE + " WHERE d.id = %s", (draft_id,))
        return await cur.fetchone()


async def olustur(unit_code: str, month_start: date, name: str) -> dict:
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO schedule_drafts (unit_id, month_start, name)
               SELECT id, %s, %s FROM units WHERE code = %s
               RETURNING id""",
            (month_start, name, unit_code),
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


async def calisan_kosu(draft_id: int) -> dict | None:
    """Aynı taslak için zaten süren bir koşu var mı? (çift tıklama koruması)"""
    async with cursor() as cur:
        await cur.execute(
            _KOSU + " WHERE r.draft_id = %s AND r.status = 'CALISIYOR' ORDER BY r.started_at DESC LIMIT 1",
            (draft_id,),
        )
        return await cur.fetchone()


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
