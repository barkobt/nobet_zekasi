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
                       'assignment_tasks_check_exclusivity'))                     AS trigger_sayisi,
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name='schedule_drafts' AND column_name='period')                AS m012_period,
    -- month_start HÂLÂ varsa 012 uygulanmamış demektir
    (SELECT count(*) FROM information_schema.columns
      WHERE table_name='schedule_drafts' AND column_name='month_start')           AS m012_eski
"""


async def kontrol() -> dict:
    async with cursor() as cur:
        await cur.execute(_BEKLENEN)
        satir = await cur.fetchone()

    # Her migration'ın bıraktığı ize ayrı ayrı bak. Eksik olanı ADIYLA söyle:
    # "şema eski" demek yetmiyor, hangi migration'ın eksik olduğu lazım.
    eksik: list[str] = []
    if satir["m010_kind"] != 1:
        eksik.append("010 (competencies.kind)")
    if satir["m011_kolon"] != 2 or satir["trigger_sayisi"] != 2:
        eksik.append("011 (kapsama kolonları / trigger'lar)")
    if satir["m012_period"] != 1 or satir["m012_eski"] != 0:
        eksik.append("012 (schedule_drafts.period)")
    sema_guncel = not eksik
    return {
        "tablo": satir["tablo"],
        "view": satir["view"],
        "aktif_personel": satir["aktif_personel"],
        "sema_guncel": sema_guncel,
        "eksik_migration": ", ".join(eksik) if eksik else None,
    }
