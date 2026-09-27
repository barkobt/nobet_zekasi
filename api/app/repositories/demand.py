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


async def satir_ekle(template_id: int, shift_code: str, slot_code: str,
                     min_count: int, competency_codes: list[str]) -> dict | None:
    """Yeni şablon satırı. slot_code ile aynı adlı yetkinlik varsa otomatik bağlanır
    (seeds/006'daki kalıp: slot kodu = yetkinlik kodu)."""
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO need_template_rows (need_template_id, shift_type_id, slot_code, min_count)
               SELECT %s, st.id, %s, %s
               FROM shift_types st JOIN units u ON u.id = st.unit_id
               WHERE st.code = %s AND u.code = 'ACIL_SERVIS'
               RETURNING id""",
            (template_id, slot_code, min_count, shift_code),
        )
        if (yeni := await cur.fetchone()) is None:
            return None

        # Kurala bağla: aynı slotun başka vardiyadaki satırı hangi kurala bağlıysa
        # bu da ona bağlanır. Docstring bunu vaat ediyordu ama kod yapmıyordu.
        await cur.execute(
            """UPDATE need_template_rows ntr
                  SET constraint_id = (
                      SELECT o.constraint_id FROM need_template_rows o
                       WHERE o.slot_code = ntr.slot_code AND o.id <> ntr.id
                         AND o.constraint_id IS NOT NULL
                       LIMIT 1)
                WHERE ntr.id = %s""",
            (yeni["id"],),
        )

        if competency_codes:
            await cur.execute(
                """INSERT INTO need_template_row_competencies (need_template_row_id, competency_id)
                   SELECT %s, id FROM competencies WHERE code = ANY(%s)
                   ON CONFLICT DO NOTHING""",
                (yeni["id"], competency_codes),
            )
        return yeni


async def satir_sil(row_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            "DELETE FROM need_template_rows WHERE id = %s RETURNING id", (row_id,)
        )
        return await cur.fetchone()
