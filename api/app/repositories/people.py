"""E-04 Personel — düz SQL.

AD/SOYAD NOTU: şemada tek bir `staff.full_name` var. Arayüz ad ve soyadı ayrı
sütunlarda istiyor; son boşluktan bölüp gösteriyor, yazarken boşlukla birleştiriyoruz.
Tek kelimelik soyadları için güvenli. Gerçekten ayrı alanlar isteniyorsa bu bir
migration işidir (CLAUDE.md: şemada eksik görürsen dur ve yeni migration öner).
"""

from datetime import date, timedelta

from app.db import cursor

_LISTE = """
SELECT s.id, s.sicil_no, s.full_name, s.shift_eligibility, s.is_active,
       s.is_orientation, s.seniority_years, s.note,
       r.code AS role_code, r.name AS role_name,
       s.buddy_staff_id, b.full_name AS buddy_name,
       (SELECT count(*) FROM assignments a WHERE a.staff_id = s.id) AS assignment_count,
       c.monthly_target_hours, c.valid_period AS contract_period,
       -- Sözleşmede hedef boşsa kural varsayılanı geçerli (monthly_min_hours).
       -- Sütunu boş bırakmak yerine ETKİN hedefi gösteriyoruz; hangisi olduğu
       -- target_is_default ile bildiriliyor.
       (SELECT p.param_value FROM constraint_params p
         JOIN constraints k ON k.id = p.constraint_id
        WHERE k.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours') AS kural_hedefi
FROM staff s
JOIN roles r      ON r.id = s.role_id
LEFT JOIN staff b ON b.id = s.buddy_staff_id
LEFT JOIN LATERAL (
    -- Bugün geçerli sözleşme; yoksa en yenisi
    SELECT k.monthly_target_hours, k.valid_period
    FROM contracts k
    WHERE k.staff_id = s.id
    ORDER BY (k.valid_period @> CURRENT_DATE) DESC, lower(k.valid_period) DESC
    LIMIT 1
) c ON TRUE
"""

_SIRA = """
ORDER BY CASE r.code
           WHEN 'sorumlu_hemsire' THEN 1
           WHEN 'egitim_hemsire'  THEN 2
           WHEN 'shift_yetkilisi' THEN 3
           ELSE 4
         END, s.full_name
"""


async def listele(*, arama: str | None = None, sadece_aktif: bool = True) -> list[dict]:
    kosullar, parametreler = [], []
    if sadece_aktif:
        kosullar.append("s.is_active")
    if arama:
        kosullar.append("(s.full_name ILIKE %s OR COALESCE(s.sicil_no,'') ILIKE %s)")
        parametreler += [f"%{arama}%", f"%{arama}%"]
    where = (" WHERE " + " AND ".join(kosullar)) if kosullar else ""
    async with cursor() as cur:
        await cur.execute(_LISTE + where + _SIRA, parametreler)
        return await cur.fetchall()


async def getir(staff_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute(_LISTE + " WHERE s.id = %s", (staff_id,))
        return await cur.fetchone()


async def roller() -> list[dict]:
    async with cursor() as cur:
        await cur.execute("SELECT code, name FROM roles ORDER BY id")
        return await cur.fetchall()


async def detay(staff_id: int) -> dict:
    async with cursor() as cur:
        await cur.execute(
            """SELECT id, lower(valid_period) AS valid_from, upper(valid_period) AS valid_to,
                      monthly_target_hours, note
               FROM contracts WHERE staff_id = %s ORDER BY lower(valid_period) DESC""",
            (staff_id,),
        )
        sozlesmeler = await cur.fetchall()

        await cur.execute(
            """SELECT id, lower(period) AS bas, upper(period) AS bitis, absence_type, note
               FROM absences WHERE staff_id = %s ORDER BY lower(period) DESC""",
            (staff_id,),
        )
        izinler = await cur.fetchall()

        await cur.execute(
            """SELECT id, target_date, rule_type, note
               FROM availability_rules WHERE staff_id = %s ORDER BY target_date DESC""",
            (staff_id,),
        )
        musaitlik = await cur.fetchall()

        await cur.execute(
            """SELECT v.other_staff_id, s.full_name AS other_name, v.note
               FROM v_staff_conflict_pairs v
               JOIN staff s ON s.id = v.other_staff_id
               WHERE v.staff_id = %s ORDER BY s.full_name""",
            (staff_id,),
        )
        uyumsuzluk = await cur.fetchall()

    return {"sozlesmeler": sozlesmeler, "izinler": izinler,
            "musaitlik": musaitlik, "uyumsuzluk": uyumsuzluk}


async def olustur(full_name: str, role_code: str, shift_eligibility: str,
                  sicil_no: str | None, seniority_years: float | None,
                  note: str | None) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO staff (role_id, full_name, shift_eligibility, sicil_no,
                                  seniority_years, note)
               SELECT id, %s, %s, %s, %s, %s FROM roles WHERE code = %s
               RETURNING id""",
            (full_name, shift_eligibility, sicil_no, seniority_years, note, role_code),
        )
        return await cur.fetchone()


async def guncelle(staff_id: int, alanlar: dict) -> dict | None:
    """Yalnızca gönderilen alanları günceller (PATCH semantiği)."""
    if not alanlar:
        return {"id": staff_id}
    parcalar, degerler = [], []
    for ad, deger in alanlar.items():
        if ad == "role_code":
            parcalar.append("role_id = (SELECT id FROM roles WHERE code = %s)")
        else:
            parcalar.append(f"{ad} = %s")
        degerler.append(deger)
    degerler.append(staff_id)
    async with cursor() as cur:
        await cur.execute(
            f"UPDATE staff SET {', '.join(parcalar)} WHERE id = %s RETURNING id", degerler
        )
        return await cur.fetchone()


async def sozlesme_ekle(staff_id: int, bas: date, bitis: date | None,
                        hedef: float | None, note: str | None) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO contracts (staff_id, valid_period, monthly_target_hours, note)
               VALUES (%s, daterange(%s, %s, '[)'), %s, %s) RETURNING id""",
            (staff_id, bas, bitis, hedef, note),
        )
        return await cur.fetchone()


async def izin_ekle(staff_id: int, bas: date, bitis: date,
                    tur: str, note: str | None) -> dict | None:
    """bitis KAPSAYICI gelir, DATERANGE dışlayıcı tutar."""
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO absences (staff_id, period, absence_type, note)
               VALUES (%s, daterange(%s, %s, '[)'), %s, %s) RETURNING id""",
            (staff_id, bas, bitis + timedelta(days=1), tur, note),
        )
        return await cur.fetchone()


async def izin_sil(absence_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute("DELETE FROM absences WHERE id = %s RETURNING id", (absence_id,))
        return await cur.fetchone()


async def musaitlik_ekle(staff_id: int, gun: date, tur: str, note: str | None) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO availability_rules (staff_id, target_date, rule_type, note)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (staff_id, target_date, rule_type) DO UPDATE SET note = EXCLUDED.note
               RETURNING id""",
            (staff_id, gun, tur, note),
        )
        return await cur.fetchone()


async def musaitlik_sil(rule_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute("DELETE FROM availability_rules WHERE id = %s RETURNING id", (rule_id,))
        return await cur.fetchone()


async def uyumsuzluk_ekle(a: int, b: int, note: str | None) -> None:
    """Tablo çifti (küçük id, büyük id) olarak tutuyor — sıralamayı burada yapıyoruz."""
    dusuk, yuksek = (a, b) if a < b else (b, a)
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO staff_conflicts (staff_id_low, staff_id_high, note)
               VALUES (%s, %s, %s)
               ON CONFLICT (staff_id_low, staff_id_high) DO UPDATE SET note = EXCLUDED.note""",
            (dusuk, yuksek, note),
        )


async def uyumsuzluk_sil(a: int, b: int) -> None:
    dusuk, yuksek = (a, b) if a < b else (b, a)
    async with cursor() as cur:
        await cur.execute(
            "DELETE FROM staff_conflicts WHERE staff_id_low = %s AND staff_id_high = %s",
            (dusuk, yuksek),
        )


async def sil(staff_id: int) -> bool:
    """Ataması olan personel SİLİNMEZ (fk_assignments_staff RESTRICT).

    Çağıran önce assignment_count'a bakıp "Pasife al" önermeli; bu fonksiyon
    yalnız gerçekten silinebilir olanı siler.
    """
    async with cursor() as cur:
        await cur.execute("DELETE FROM staff WHERE id = %s RETURNING id", (staff_id,))
        return await cur.fetchone() is not None


async def sozlesme_guncelle(contract_id: int, bas, bitis, hedef, note) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            """UPDATE contracts
                  SET valid_period = daterange(%s, %s, '[)'),
                      monthly_target_hours = %s, note = %s
                WHERE id = %s RETURNING id""",
            (bas, bitis, hedef, note, contract_id),
        )
        return await cur.fetchone()


async def sozlesme_sil(contract_id: int) -> dict | None:
    async with cursor() as cur:
        await cur.execute("DELETE FROM contracts WHERE id = %s RETURNING id", (contract_id,))
        return await cur.fetchone()


async def izin_guncelle(absence_id: int, bas, bitis, tur: str, note) -> dict | None:
    """bitis KAPSAYICI gelir."""
    async with cursor() as cur:
        await cur.execute(
            """UPDATE absences
                  SET period = daterange(%s, %s, '[)'), absence_type = %s, note = %s
                WHERE id = %s RETURNING id""",
            (bas, bitis + timedelta(days=1), tur, note, absence_id),
        )
        return await cur.fetchone()
