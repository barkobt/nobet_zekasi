"""E-06 İhtiyaç — düz SQL."""

from datetime import date

from app.db import cursor

# Minimum kadro saati: GENEL slotu × vardiya süresi. Diğer slotlar aynı kadronun
# içinden atanır (C-019), onları toplamak aynı kişiyi birkaç kez saymak olurdu.
_GEREKEN_SAAT = """
SELECT COALESCE(SUM(ntr.min_count * st.duration_hours), 0) AS gereken
FROM generate_series(%(bas)s::date, %(bitis)s::date - 1, INTERVAL '1 day') gs
JOIN need_periods np        ON np.valid_period @> gs::date
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
                           AND ntr.slot_code = 'GENEL'
JOIN shift_types st         ON st.id = ntr.shift_type_id AND st.is_active
"""

_SABLON = """
SELECT nt.id AS template_id, nt.code AS template_code, nt.name AS template_name,
       ntr.id, ntr.slot_code, ntr.min_count,
       st.code AS shift_code, st.name AS shift_name, st.start_time,
       c.code AS constraint_code, c.catalog_code, c.name AS constraint_name, c.is_hard,
       COALESCE(y.kodlar, ARRAY[]::text[]) AS competency_codes
FROM need_templates nt
JOIN need_template_rows ntr ON ntr.need_template_id = nt.id
JOIN shift_types st         ON st.id = ntr.shift_type_id
LEFT JOIN constraints c     ON c.id = ntr.constraint_id
LEFT JOIN LATERAL (
    SELECT array_agg(comp.code ORDER BY comp.code) AS kodlar
    FROM need_template_row_competencies x
    JOIN competencies comp ON comp.id = x.competency_id
    WHERE x.need_template_row_id = ntr.id
) y ON TRUE
ORDER BY nt.id, st.start_time, ntr.slot_code
"""


async def gereken_saat(bas: date, bitis: date) -> float:
    async with cursor() as cur:
        await cur.execute(_GEREKEN_SAAT, {"bas": bas, "bitis": bitis})
        return float((await cur.fetchone())["gereken"])


async def sablon() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_SABLON)
        return await cur.fetchall()


async def satir_guncelle(row_id: int, min_count: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            "UPDATE need_template_rows SET min_count = %s WHERE id = %s RETURNING id",
            (min_count, row_id),
        )
        return await cur.fetchone()
