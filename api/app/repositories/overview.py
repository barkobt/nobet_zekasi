"""Ana sayfa kartı — düz SQL."""

from datetime import date

from app.db import cursor

# Seçili dönemle ÇAKIŞAN taslak: önce yayınlanmış, yoksa en yeni taslak.
# Aralık çakışması (&&) kullanılıyor çünkü kullanıcının seçtiği dönem ile taslağın
# dönemi birebir aynı olmak zorunda değil (hafta seçiliyken aylık taslak da sayılır).
_TASLAK = """
SELECT d.id, d.name, d.status, u.name AS unit_name,
       (SELECT r.params_snapshot ->> 'solver' FROM solver_runs r
         WHERE r.draft_id = d.id ORDER BY r.started_at DESC LIMIT 1) AS solver_impl
FROM schedule_drafts d
JOIN units u ON u.id = d.unit_id
WHERE d.period && daterange(%(bas)s, %(bitis)s, '[)')
ORDER BY (d.status = 'yayinlandi') DESC, lower(d.period) DESC, d.id DESC
LIMIT 1
"""

# GEREKEN SAAT — ihtiyaç şablonundan türetilir:
#   her gün × o gün geçerli şablonun her vardiyası için
#   GENEL slotunun min_count'u × vardiyanın NET süresi (mola hariç, migration 023)
# GENEL seçilmesinin sebebi: diğer slotlar (triyaj, gözlem, ambulans) aynı kadronun
# İÇİNDEN atanır, ek kişi değildir (C-019). Onları da toplasaydık aynı kişiyi
# birkaç kez sayardık.
# NET olmak ZORUNDA: "atanan saat"in paydası bu. Pay net, payda brüt olursa
# E-00'daki oran iki farklı birimi karşılaştırır.
_GEREKEN = """
SELECT COALESCE(ROUND(SUM(ntr.min_count * st.net_minutes) / 60.0, 2), 0) AS gereken
FROM generate_series(%(bas)s::date, %(bitis)s::date - 1, INTERVAL '1 day') gs
JOIN need_periods np        ON np.valid_period @> gs::date
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
                           AND ntr.slot_code = 'GENEL'
JOIN v_shift_types_net st   ON st.id = ntr.shift_type_id AND st.is_active
"""

# ATANAN SAAT — dönemdeki atamaların planlanan NET saatleri (mola hariç, 023).
_ATANAN = """
SELECT COALESCE(ROUND(SUM(h.planned_net_minutes) / 60.0, 2), 0) AS atanan
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
    -- Adalet farkı YALNIZ adalet havuzundan: sorumlu hemşirenin programı sabit,
    -- oryantasyondakiler eğitmenlerini gölgelediği için saatleri yüksek, ayrılan
    -- ve ay içinde başlayanlar ayın tamamını çalışmıyor. Hepsini katmak farkı
    -- yanlış büyütüyor ve ana sayfa ile çizelge ekranı farklı sayı söylüyordu.
    -- Ölçüt solver/data.py → Personel.adalete_girer ile aynı.
    COALESCE((SELECT max(m.net_hours) - min(m.net_hours)
                FROM v_monthly_hours m
                JOIN staff s  ON s.id = m.staff_id
                JOIN roles r  ON r.id = s.role_id
               WHERE m.draft_id = %(draft_id)s AND m.net_hours > 0
                 AND NOT s.is_orientation
                 AND r.code <> 'sorumlu_hemsire'
                 AND EXISTS (SELECT 1 FROM contracts ct
                              WHERE ct.staff_id = s.id
                                AND ct.valid_period @> (SELECT period FROM schedule_drafts
                                                         WHERE id = %(draft_id)s))), 0) AS adalet
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
