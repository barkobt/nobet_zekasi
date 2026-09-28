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

# Hangi sayaç görünecek: ayar veritabanında (visible_counters). Hesap her sayaç için
# YAPILIR, görünürlük bayrağı yanında taşınır — arayüz açıp kapatırken yeni istek atmaz.
_SAYACLAR = """
SELECT key, badge, label, always_shown, weekly_on, monthly_on
FROM visible_counters ORDER BY sort_order
"""

# Vardiya süreleri: satır sayaçlarının saat toplamı buradan çıkar. Saat kodda
# gömülü DEĞİL — GECE_0100 gibi sonradan eklenen vardiyalar kendiliğinden doğru sayılır.
_VARDIYA_SURELERI = """
SELECT code, duration_hours, crosses_midnight FROM shift_types
"""

# İSTEK sayacı (İST): görünen aralıkta karşılanamayan "mümkünse" tercihleri.
# KESIN istekler katı kural — karşılanmamaları zaten kontrolcünün işi, sayaca girmez.
_ISTEKLER = """
SELECT ar.staff_id, ar.target_date, ar.rule_type, ar.status
FROM availability_rules ar
WHERE ar.status = 'MUMKUNSE'
  AND ar.target_date BETWEEN %(gun_bas)s AND %(gun_son)s
"""

# Hedef saatler kodda değil veritabanında (app/hedef.py bunları kullanır).
_HEDEF_PARAMETRELERI = """
SELECT p.param_key, p.param_value
FROM constraint_params p
WHERE p.param_key IN ('monthly_min_hours', 'weekly_reference_hours')
"""

# Ayrılan personel: aktif değil ama bu taslakta ÇALIŞMIŞSA satırı görünmeli — kağıt
# Eylül'de Efe ve Çağla'nın atamaları var, gizlenirse çizelge kağıtla uyuşmaz.
#
# adalete_girer: hastane kararı — sorumlu hemşire ve oryantasyondakiler mevcuda
# sayılmaz; ayın tamamında sözleşmesi olmayan (ayrılan / sonradan başlayan) mevcuda
# SAYILIR ama saat adaleti ve 200 saat karşılaştırmasına girmez. solver/data.py'deki
# Personel.adalete_girer ile aynı kural: ekran ve solver aynı rakamı söylesin.
_PERSONEL = """
SELECT s.id, s.full_name, s.is_orientation, s.is_active,
       r.code AS role_code, r.name AS role_name,
       (NOT s.is_orientation
        AND r.code <> 'sorumlu_hemsire'
        AND EXISTS (SELECT 1 FROM contracts ct
                     WHERE ct.staff_id = s.id
                       AND ct.valid_period @> (SELECT period FROM schedule_drafts
                                                WHERE id = %(draft_id)s))
       ) AS adalete_girer
FROM staff s
JOIN roles r ON r.id = s.role_id
WHERE s.is_active
   OR EXISTS (SELECT 1 FROM assignments a
               WHERE a.staff_id = s.id AND a.draft_id = %(draft_id)s)
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
SELECT d.id, d.name, d.status, d.created_at, u.name AS unit_name,
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
        await cur.execute(_PERSONEL, p)
        personel = await cur.fetchall()

        await cur.execute(_ATAMALAR, p)
        atamalar = await cur.fetchall()

        await cur.execute(_KAPSAMA, p)
        kapsama = await cur.fetchall()

        await cur.execute(_AYLIK, {"draft_id": draft_id})
        aylik = await cur.fetchall()

        await cur.execute(_IZINLER, p)
        izinler = await cur.fetchall()

        await cur.execute(_HEDEF_PARAMETRELERI)
        hedefler = {r["param_key"]: float(r["param_value"]) for r in await cur.fetchall()}

        await cur.execute(_VARDIYA_SURELERI)
        vardiyalar = {r["code"]: r for r in await cur.fetchall()}

        await cur.execute(_ISTEKLER, {"gun_bas": gun_bas, "gun_son": gun_son})
        istekler = await cur.fetchall()

        await cur.execute(_SAYACLAR)
        sayaclar = await cur.fetchall()

    return {
        "personel": personel,
        "atamalar": atamalar,
        "kapsama": kapsama,
        "aylik": aylik,
        "izinler": izinler,
        "hedefler": hedefler,
        "vardiyalar": vardiyalar,
        "istekler": istekler,
        "sayaclar": sayaclar,
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


# ---------------------------------------------------------------- sayaçlar
# Satır özeti ve alt bardaki bütün sayaçlar BURADA hesaplanır. Izgara, aylık
# görünüm ve alt bar aynı sayıyı iki yerde hesaplamasın: bir sayacın tanımı
# değişirse tek bir yer değişir.

def sayac_degerleri(
    staff_id: int,
    hucreler: dict[str, dict],
    gunler: list[date],
    vardiyalar: dict[str, dict],
    istekler: list[dict],
    hedef: float | None,
) -> dict[str, float]:
    """Bir kişinin GÖRÜNEN ARALIKTAKİ sayaçları.

    `hucreler`: ISO tarih → {"shift_code", "tasks"}. Aralığın dışı çağırana ait.
    Saat toplamı vardiya süresinden gelir, hedef farkı dönem hedefinden.
    """
    gunduz = gece = 0
    saat = 0.0
    triyaj = gozlem = ambulans = 0
    hafta_sonu = pazar = 0

    for iso, h in hucreler.items():
        vd = vardiyalar.get(h["shift_code"])
        if vd is None:
            continue
        if vd["crosses_midnight"]:
            gece += 1
        else:
            gunduz += 1
        saat += float(vd["duration_hours"])

        gorevler = set(h.get("tasks") or ())
        triyaj += "TRIYAJ" in gorevler
        gozlem += "GOZLEM" in gorevler
        ambulans += "AMBULANS" in gorevler

        g = date.fromisoformat(iso)
        if g.isoweekday() >= 6:
            hafta_sonu += 1
        if g.isoweekday() == 7:
            pazar += 1

    # Boş gün: o gün hiç vardiya BAŞLAMAYAN gün. İzin de boş gündür — kişi
    # çalışmıyor. Gece vardiyasının ertesi günü de boştur (vardiya bir önceki
    # gün başladı), bu yüzden "başlayan vardiya" ölçütü doğru olan.
    bos_gun = sum(1 for g in gunler if g.isoformat() not in hucreler)

    # Karşılanamayan "mümkünse" tercihler. Tür başına ayrı ölçüt:
    #   BOS_GUN        → o gün çalışmışsa karşılanmadı
    #   SADECE_GUNDUZ  → o gün gece çalışmışsa karşılanmadı
    #   SADECE_GECE    → o gün gündüz çalışmışsa karşılanmadı
    karsilanmayan = 0
    for i in istekler:
        if i["staff_id"] != staff_id:
            continue
        h = hucreler.get(i["target_date"].isoformat())
        if h is None:
            continue                     # o gün çalışmıyor → BOS_GUN karşılandı
        vd = vardiyalar.get(h["shift_code"])
        gece_mi = bool(vd and vd["crosses_midnight"])
        tur = i["rule_type"]
        if tur in ("BOS_GUN", "off_talebi"):
            karsilanmayan += 1
        elif tur == "SADECE_GUNDUZ" and gece_mi:
            karsilanmayan += 1
        elif tur == "SADECE_GECE" and not gece_mi:
            karsilanmayan += 1

    saat = round(saat, 1)
    return {
        "G": gunduz,
        "N": gece,
        "S": saat,
        "HF": round(saat - hedef, 1) if hedef is not None else None,
        "TRY": triyaj,
        "GOZ": gozlem,
        "AMB": ambulans,
        "HS": hafta_sonu,
        "PZ": pazar,
        "BG": bos_gun,
        "IST": karsilanmayan,
    }
