"""E-09 çizelgesi — düz SQL. Üç sorgu: atamalar, kapsama, aylık toplam."""

from datetime import date

from app.db import cursor

# Gün başlıklarındaki sayaçlar ve tooltip kırılımı. v_daily_coverage zaten
# kind'a göre (migration 010) doğru sayıyor; burada yalnızca aralığa süzülüyor.
_KAPSAMA = """
SELECT cov.day, cov.shift_code, cov.slot_code, cov.assigned, cov.required
FROM v_daily_coverage cov
WHERE cov.draft_id = %(draft_id)s
  AND cov.day BETWEEN %(gun_bas)s AND %(gun_son)s
ORDER BY cov.day, cov.shift_code DESC, cov.slot_code
"""

# Hücreler. Görev rozetleri tek sorguda toplanıyor (N+1 yok).
_ATAMALAR = """
SELECT a.staff_id,
       a.work_date,
       st.code AS shift_code,
       st.crosses_midnight,
       a.is_locked,
       a.source,
       COALESCE(g.kodlar, ARRAY[]::text[]) AS tasks
FROM assignments a
JOIN shift_types st ON st.id = a.shift_type_id
LEFT JOIN LATERAL (
    SELECT array_agg(c.code ORDER BY c.code) AS kodlar
    FROM assignment_tasks t
    JOIN competencies c ON c.id = t.competency_id
    WHERE t.assignment_id = a.id
) g ON TRUE
WHERE a.draft_id = %(draft_id)s
  AND a.work_date BETWEEN %(gun_bas)s AND %(gun_son)s
"""

# Satır sonu: aylık toplam ve 200 saat hedefine uzaklık.
# v_monthly_hours ayın TAMAMINI sayar — seçili hafta değil. Satır sonu zaten
# "kişinin aylık toplamı" demek (DESIGN §6), o yüzden doğru olan bu.
_AYLIK = """
SELECT mh.staff_id, mh.shift_count, mh.planned_hours, mh.worked_hours,
       mh.min_hours, mh.overtime_max
FROM v_monthly_hours mh
WHERE mh.draft_id = %(draft_id)s
"""

_PERSONEL = """
SELECT s.id, s.full_name, s.is_orientation, r.code AS role_code, r.name AS role_name
FROM staff s
JOIN roles r ON r.id = s.role_id
WHERE s.is_active
ORDER BY CASE r.code
           WHEN 'sorumlu_hemsire' THEN 1
           WHEN 'egitim_hemsire'  THEN 2
           WHEN 'shift_yetkilisi' THEN 3
           ELSE 4
         END, s.full_name
"""

_IZINLER = """
SELECT ab.staff_id, ab.absence_type, ab.period
FROM absences ab
WHERE ab.period && daterange(%(gun_bas)s, %(gun_son)s, '[]')
"""

# ilk_gun / son_gun: taslak ayın TAMAMINI kapsıyor mu? Aylık hedef karşılaştırması
# (C-004, kişi başı 200 saat) yalnızca tam aylık taslakta anlamlıdır.
_TASLAK = """
SELECT d.id, d.name, d.month_start, d.status, u.name AS unit_name,
       (SELECT min(work_date) FROM assignments WHERE draft_id = d.id) AS ilk_gun,
       (SELECT max(work_date) FROM assignments WHERE draft_id = d.id) AS son_gun
FROM schedule_drafts d
JOIN units u ON u.id = d.unit_id
WHERE d.id = %(draft_id)s
"""


async def taslak(draft_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_TASLAK, {"draft_id": draft_id})
        return await cur.fetchone()


async def cizelge_verisi(draft_id: int, gun_bas: date, gun_son: date) -> dict:
    """Ekranın tamamını besleyen ham satırlar. Biçimlendirme router'da."""
    p = {"draft_id": draft_id, "gun_bas": gun_bas, "gun_son": gun_son}
    async with cursor() as cur:
        await cur.execute(_PERSONEL)
        personel = await cur.fetchall()

        await cur.execute(_ATAMALAR, p)
        atamalar = await cur.fetchall()

        await cur.execute(_KAPSAMA, p)
        kapsama = await cur.fetchall()

        await cur.execute(_AYLIK, {"draft_id": draft_id})
        aylik = await cur.fetchall()

        await cur.execute(_IZINLER, p)
        izinler = await cur.fetchall()

    return {
        "personel": personel,
        "atamalar": atamalar,
        "kapsama": kapsama,
        "aylik": aylik,
        "izinler": izinler,
    }
