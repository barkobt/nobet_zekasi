"""Sağlık kontrolü — havuzun çalıştığını ve şemanın kodla uyumlu olduğunu kanıtlar."""

from app.db import cursor

# Kodun ihtiyaç duyduğu, en son migration'ların getirdiği nesneler.
# Burada yoklanması, "deploy edilen kod ile deploy edilen şema aynı mı?" sorusunu
# gözlemlenebilir bir olguya çeviriyor — aksi halde hata ancak ekran açılınca görülür.
_BEKLENEN = """
SELECT
    (SELECT count(*) FROM information_schema.tables
      WHERE table_schema='public' AND table_type='BASE TABLE')                    AS tablo,
    (SELECT count(*) FROM information_schema.views WHERE table_schema='public')   AS view,
    (SELECT count(*) FROM staff WHERE is_active)                                  AS aktif_personel,
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name='competencies' AND column_name='kind')                     AS m010_kind,
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name='v_daily_coverage'
        AND column_name IN ('qualified','remaining_after_ambulance'))             AS m011_kolon,
    (SELECT count(*) FROM pg_trigger
      WHERE tgname IN ('assignment_tasks_check_eligibility',
                       'assignment_tasks_check_exclusivity'))                     AS trigger_sayisi
"""


async def kontrol() -> dict:
    async with cursor() as cur:
        await cur.execute(_BEKLENEN)
        satir = await cur.fetchone()

    # 010: kind kolonu · 011: iki ölçü kolonu · iki trigger
    sema_guncel = (
        satir["m010_kind"] == 1
        and satir["m011_kolon"] == 2
        and satir["trigger_sayisi"] == 2
    )
    return {
        "tablo": satir["tablo"],
        "view": satir["view"],
        "aktif_personel": satir["aktif_personel"],
        "sema_guncel": sema_guncel,
    }
