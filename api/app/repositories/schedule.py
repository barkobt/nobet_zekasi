"""E-09 çizelgesi — düz SQL. Üç sorgu: atamalar, kapsama, aylık toplam."""

from datetime import date, timedelta

from app.db import cursor

# Gün başlıklarındaki sayaçlar ve tooltip kırılımı. v_daily_coverage zaten
# kind'a göre (migration 010) doğru sayıyor; burada yalnızca aralığa süzülüyor.
_KAPSAMA = """
SELECT cov.day, cov.shift_code, cov.slot_code, cov.assigned, cov.required,
       cov.qualified, cov.remaining_after_ambulance
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

# ilk_gun / son_gun: atamalar taslağın aralığının TAMAMINI kapsıyor mu? Aylık hedef karşılaştırması
# (C-004, kişi başı 200 saat) yalnızca tam aylık taslakta anlamlıdır.
_TASLAK = """
SELECT d.id, d.name, d.status, u.name AS unit_name,
       lower(d.period) AS period_start,
       upper(d.period) AS period_end,
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


async def hucre_yaz(draft_id: int, staff_id: int, gun: date,
                    shift_code: str, tasks: list[str]) -> tuple[bool, list[str]]:
    """Elle hücre düzenleme. source='manuel', is_locked=TRUE → solver dokunmaz.

    Kural uyarıları ENGELLEMEZ, yalnız bildirilir (docs/ekran-haritasi.md E-09:
    "hangi kuralın ihlal edildiğini anında söyler, engellemez").

    DİKKAT — transaction: tek bir cursor() bağlamı tek transaction demek.
    Bir INSERT veritabanı kısıtına takılırsa transaction ABORT olur ve o ana
    kadarki DELETE'ler de geri alınır. Bu yüzden çakışma kontrolleri INSERT'ten
    ÖNCE sorguyla yapılıyor; istisna yakalayıp devam etmek işe yaramaz.

    Dönüş: (yazildi, uyarilar). "Reddedildi" ile "yazıldı ama uyarı var" ayrı
    şeyler; arayüz ikisini karıştırırsa kullanıcı yazılmayan hücreyi kaydedilmiş sanar.
    """
    uyarilar: list[str] = []
    NOT_METNI = "Çizelgeden işaretlendi"

    async with cursor() as cur:
        # Yazmadan önce doğrula: hücre taslağın dönemi içinde mi, kişi aktif mi?
        # Aksi halde ızgarada görünmeyen ama sayaçlara giren satırlar oluşuyordu.
        await cur.execute(
            "SELECT period FROM schedule_drafts WHERE id = %s", (draft_id,)
        )
        if (t := await cur.fetchone()) is None:
            return False, ["Taslak bulunamadı."]
        if not (t["period"].lower <= gun < t["period"].upper):
            return False, ["Bu gün taslağın dönemi dışında."]

        await cur.execute("SELECT full_name, is_active FROM staff WHERE id = %s", (staff_id,))
        if (kisi := await cur.fetchone()) is None:
            return False, ["Personel bulunamadı."]
        if not kisi["is_active"]:
            return False, [f"{kisi['full_name']} pasif; çizelgeye yazılamaz."]

        # İZİN: çakışma olup olmadığını ÖNCE sor, sonra yaz.
        if shift_code == "IZIN":
            await cur.execute(
                """SELECT 1 FROM absences
                    WHERE staff_id = %s AND period && daterange(%s, %s, '[)')
                      AND note IS DISTINCT FROM %s""",
                (staff_id, gun, gun + timedelta(days=1), NOT_METNI),
            )
            zaten_izinli = await cur.fetchone() is not None

            # Atama HER DURUMDA kalkar: kullanıcı "bu hücre izin olsun" dedi.
            # Eskiden çakışan izin varken erken dönülüyor ve kişi hem izinli hem
            # vardiyada görünüyordu.
            await cur.execute(
                "DELETE FROM assignments WHERE draft_id = %s AND staff_id = %s AND work_date = %s",
                (draft_id, staff_id, gun),
            )
            if zaten_izinli:
                uyarilar.append("Bu güne ait bir devamsızlık kaydı zaten vardı.")
                return True, uyarilar
            await cur.execute(
                """INSERT INTO absences (staff_id, period, absence_type, note)
                   VALUES (%s, daterange(%s, %s, '[)'), 'diger', %s)
                   ON CONFLICT DO NOTHING""",
                (staff_id, gun, gun + timedelta(days=1), NOT_METNI),
            )
            return True, uyarilar

        # Buradan sonrası atamayı değiştirir: önce o günü temizle.
        await cur.execute(
            "DELETE FROM assignments WHERE draft_id = %s AND staff_id = %s AND work_date = %s",
            (draft_id, staff_id, gun),
        )

        if shift_code == "BOS":
            await cur.execute(
                """DELETE FROM absences
                    WHERE staff_id = %s AND period = daterange(%s, %s, '[)') AND note = %s""",
                (staff_id, gun, gun + timedelta(days=1), NOT_METNI),
            )
            return True, uyarilar

        # Vardiya: çizelgeden işaretlenmiş izin varsa kalksın (ikisi aynı anda olmaz)
        await cur.execute(
            """DELETE FROM absences
                WHERE staff_id = %s AND period && daterange(%s, %s, '[)') AND note = %s""",
            (staff_id, gun, gun + timedelta(days=1), NOT_METNI),
        )
        # Elle girilmiş gerçek bir izin varsa uyar ama engelleme
        await cur.execute(
            """SELECT 1 FROM absences
                WHERE staff_id = %s AND period && daterange(%s, %s, '[)')""",
            (staff_id, gun, gun + timedelta(days=1)),
        )
        if await cur.fetchone() is not None:
            uyarilar.append("Bu kişi o gün izinli görünüyor.")

        await cur.execute(
            """INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date,
                                        source, is_locked)
               SELECT %s, %s, st.id, %s, 'manuel', TRUE
               FROM shift_types st JOIN units u ON u.id = st.unit_id
               WHERE st.code = %s AND u.code = 'ACIL_SERVIS' AND st.is_active
               RETURNING id""",
            (draft_id, staff_id, gun, shift_code),
        )
        if (atama := await cur.fetchone()) is None:
            return False, ["Vardiya tipi bulunamadı."]

        if shift_code == "GECE":
            await cur.execute(
                "SELECT full_name FROM staff WHERE id = %s AND shift_eligibility = 'sadece_gunduz'",
                (staff_id,),
            )
            if (k := await cur.fetchone()) is not None:
                uyarilar.append(f"{k['full_name']} yalnız gündüz çalışabiliyor.")

        if not tasks:
            return True, uyarilar

        if "TRIYAJ" in tasks and "GOZLEM" in tasks:
            uyarilar.append("Triyaj ve gözlem aynı vardiyada aynı kişiye verilemez.")
            tasks = [t for t in tasks if t != "GOZLEM"]

        await cur.execute(
            """SELECT c.name FROM competencies c
                WHERE c.code = ANY(%s)
                  AND NOT EXISTS (SELECT 1 FROM staff_competencies sc
                                  WHERE sc.staff_id = %s AND sc.competency_id = c.id)""",
            (tasks, staff_id),
        )
        for eksik in await cur.fetchall():
            uyarilar.append(f"Bu kişide \"{eksik['name']}\" yetkinliği yok.")

        await cur.execute(
            """INSERT INTO assignment_tasks (assignment_id, competency_id)
               SELECT %s, id FROM competencies WHERE code = ANY(%s) AND kind = 'TASK'""",
            (atama["id"], tasks),
        )

    return True, uyarilar
