"""E-01/E-02/E-03 — düz SQL."""

from app.db import cursor

_YETKINLIKLER = """
SELECT c.id, c.code, c.name, c.kind, c.description,
       (SELECT count(*) FROM staff_competencies sc
         JOIN staff s ON s.id = sc.staff_id
        WHERE sc.competency_id = c.id AND s.is_active) AS staff_count
FROM competencies c
ORDER BY (c.kind = 'TASK') DESC, c.id
"""

_MATRIS = """
SELECT s.id AS staff_id, s.full_name, s.is_orientation, r.name AS role_name,
       COALESCE(y.kodlar, ARRAY[]::text[]) AS codes
FROM staff s
JOIN roles r ON r.id = s.role_id
LEFT JOIN LATERAL (
    SELECT array_agg(c.code ORDER BY c.id) AS kodlar
    FROM staff_competencies sc
    JOIN competencies c ON c.id = sc.competency_id
    WHERE sc.staff_id = s.id
) y ON TRUE
WHERE s.is_active
ORDER BY CASE r.code
           WHEN 'sorumlu_hemsire' THEN 1 WHEN 'egitim_hemsire' THEN 2
           WHEN 'shift_yetkilisi' THEN 3 ELSE 4 END, s.full_name
"""

_KURALLAR = """
SELECT c.id, c.code, c.catalog_code, c.name, c.description,
       c.is_hard, c.default_weight, c.scope, c.source,
       COALESCE(p.liste, '[]'::json) AS params
FROM constraints c
LEFT JOIN LATERAL (
    SELECT json_agg(json_build_object(
               'id', x.id, 'param_key', x.param_key,
               'param_value', x.param_value, 'description', x.description
           ) ORDER BY x.param_key) AS liste
    FROM constraint_params x WHERE x.constraint_id = c.id
) p ON TRUE
ORDER BY c.is_hard DESC, c.catalog_code NULLS LAST, c.code
"""

_VARDIYALAR = """
SELECT st.id, st.code, st.name, st.start_time, st.duration_hours,
       st.crosses_midnight, st.is_active, u.name AS unit_name
FROM shift_types st
JOIN units u ON u.id = st.unit_id
ORDER BY st.is_active DESC, st.start_time, st.duration_hours
"""


async def yetkinlikler() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_YETKINLIKLER)
        return await cur.fetchall()


async def matris() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_MATRIS)
        return await cur.fetchall()


async def yetkinlik_degistir(staff_id: int, code: str, ver: bool) -> bool:
    """Kutucuk aç/kapa. Geçmiş atamalar korunur: assignment_tasks'a dokunulmaz,
    yalnızca kişinin yetkinlik kaydı değişir (bkz. migration 010'daki trigger notu)."""
    async with cursor() as cur:
        if ver:
            await cur.execute(
                """INSERT INTO staff_competencies (staff_id, competency_id)
                   SELECT %s, id FROM competencies WHERE code = %s
                   ON CONFLICT DO NOTHING""",
                (staff_id, code),
            )
        else:
            await cur.execute(
                """DELETE FROM staff_competencies
                   WHERE staff_id = %s
                     AND competency_id = (SELECT id FROM competencies WHERE code = %s)""",
                (staff_id, code),
            )
        return cur.rowcount > 0


async def kurallar() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_KURALLAR)
        return await cur.fetchall()


async def kural_guncelle(constraint_id: int, alanlar: dict) -> dict | None:
    if not alanlar:
        return {"id": constraint_id}
    parcalar = ", ".join(f"{k} = %s" for k in alanlar)
    async with cursor() as cur:
        await cur.execute(
            f"UPDATE constraints SET {parcalar} WHERE id = %s RETURNING id",
            [*alanlar.values(), constraint_id],
        )
        return await cur.fetchone()


async def param_guncelle(param_id: int, deger: float) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """UPDATE constraint_params
               SET param_value = %s, updated_at = CURRENT_TIMESTAMP
               WHERE id = %s RETURNING id""",
            (deger, param_id),
        )
        return await cur.fetchone()


async def vardiyalar() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_VARDIYALAR)
        return await cur.fetchall()
