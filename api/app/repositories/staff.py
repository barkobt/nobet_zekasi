"""staff tablosu — düz SQL. İş mantığı yok, yalnızca sorgu."""

from app.db import cursor

# Yetkinlikler tek sorguda toplanıyor: N+1 sorgu yerine bir LATERAL toplama.
# kind ayrımı (migration 010) burada da korunuyor — arayüz görev ile yetkiyi ayırabilsin.
_LISTE = """
SELECT s.id,
       s.full_name,
       s.shift_eligibility,
       s.is_orientation,
       s.is_active,
       s.seniority_years,
       s.note,
       r.code AS role_code,
       r.name AS role_name,
       b.full_name AS buddy_name,
       COALESCE(y.kodlar, ARRAY[]::text[])       AS competency_codes,
       COALESCE(y.gorevler, ARRAY[]::text[])     AS task_codes
FROM staff s
JOIN roles r       ON r.id = s.role_id
LEFT JOIN staff b  ON b.id = s.buddy_staff_id
LEFT JOIN LATERAL (
    SELECT array_agg(c.code ORDER BY c.id) AS kodlar,
           array_agg(c.code ORDER BY c.id) FILTER (WHERE c.kind = 'TASK') AS gorevler
    FROM staff_competencies sc
    JOIN competencies c ON c.id = sc.competency_id
    WHERE sc.staff_id = s.id
) y ON TRUE
"""


async def listele(*, sadece_aktif: bool = True) -> list[dict]:
    sql = _LISTE + ("WHERE s.is_active " if sadece_aktif else "")
    # Sıralama: sorumlu → eğitim → ekip lideri → hemşire, sonra ada göre.
    # Arayüz E-09'da da bu gruplamayı kullanıyor (DESIGN §6).
    sql += """
        ORDER BY CASE r.code
                   WHEN 'sorumlu_hemsire' THEN 1
                   WHEN 'egitim_hemsire'  THEN 2
                   WHEN 'shift_yetkilisi' THEN 3
                   ELSE 4
                 END,
                 s.full_name
    """
    async with cursor() as cur:
        await cur.execute(sql)
        return await cur.fetchall()


async def getir(staff_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_LISTE + "WHERE s.id = %s", (staff_id,))
        return await cur.fetchone()
