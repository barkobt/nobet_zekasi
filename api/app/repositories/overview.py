"""Ana sayfa kartı — düz SQL."""

from datetime import date

from app.db import cursor

# Seçili dönemle ÇAKIŞAN taslak: önce yayınlanmış, yoksa en yeni taslak.
# Aralık çakışması (&&) kullanılıyor çünkü kullanıcının seçtiği dönem ile taslağın
# dönemi birebir aynı olmak zorunda değil (hafta seçiliyken aylık taslak da sayılır).
_TASLAK = """
SELECT d.id, d.name, d.status, u.name AS unit_name
FROM schedule_drafts d
JOIN units u ON u.id = d.unit_id
WHERE d.period && daterange(%(bas)s, %(bitis)s, '[)')
ORDER BY (d.status = 'yayinlandi') DESC, lower(d.period) DESC, d.id DESC
LIMIT 1
"""

# GEREKEN SAAT — ihtiyaç şablonundan türetilir:
#   her gün × o gün geçerli şablonun her vardiyası için
#   GENEL slotunun min_count'u × vardiyanın duration_hours'ı
# GENEL seçilmesinin sebebi: diğer slotlar (triyaj, gözlem, ambulans) aynı kadronun
# İÇİNDEN atanır, ek kişi değildir (C-019). Onları da toplasaydık aynı kişiyi
# birkaç kez sayardık.
_GEREKEN = """
SELECT COALESCE(SUM(ntr.min_count * st.duration_hours), 0) AS gereken
FROM generate_series(%(bas)s::date, %(bitis)s::date - 1, INTERVAL '1 day') gs
JOIN need_periods np        ON np.valid_period @> gs::date
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
                           AND ntr.slot_code = 'GENEL'
JOIN shift_types st         ON st.id = ntr.shift_type_id AND st.is_active
"""

# ATANAN SAAT — dönemdeki atamaların planlanan saatleri.
_ATANAN = """
SELECT COALESCE(SUM(h.planned_hours), 0) AS atanan
FROM v_assignment_hours h
WHERE h.draft_id = %(draft_id)s
  AND h.work_date >= %(bas)s AND h.work_date < %(bitis)s
"""

_METRIK = """
SELECT
    (SELECT count(*) FROM v_daily_coverage c
      WHERE c.draft_id = %(draft_id)s AND c.assigned < c.required
        AND c.day >= %(bas)s AND c.day < %(bitis)s)                    AS ihlal,
    COALESCE((SELECT sum(m.overtime_max) FROM v_monthly_hours m
               WHERE m.draft_id = %(draft_id)s), 0)                    AS fazla_mesai,
    COALESCE((SELECT max(m.worked_hours) - min(m.worked_hours) FROM v_monthly_hours m
               WHERE m.draft_id = %(draft_id)s AND m.worked_hours > 0), 0) AS adalet
"""

_BIRIM = "SELECT name FROM units ORDER BY id LIMIT 1"


async def ozet(bas: date, bitis: date) -> dict:
    p = {"bas": bas, "bitis": bitis}
    async with cursor() as cur:
        await cur.execute(_TASLAK, p)
        taslak = await cur.fetchone()

        await cur.execute(_GEREKEN, p)
        gereken = float((await cur.fetchone())["gereken"])

        if taslak is None:
            await cur.execute(_BIRIM)
            return {"taslak": None, "birim": (await cur.fetchone())["name"],
                    "gereken": gereken, "atanan": 0.0,
                    "ihlal": 0, "fazla_mesai": 0.0, "adalet": 0.0}

        pd = {**p, "draft_id": taslak["id"]}
        await cur.execute(_ATANAN, pd)
        atanan = float((await cur.fetchone())["atanan"])
        await cur.execute(_METRIK, pd)
        m = await cur.fetchone()

    return {
        "taslak": taslak, "birim": taslak["unit_name"], "gereken": gereken, "atanan": atanan,
        "ihlal": m["ihlal"], "fazla_mesai": float(m["fazla_mesai"]), "adalet": float(m["adalet"]),
    }
