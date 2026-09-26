"""Sağlık kontrolü — havuzun gerçekten çalıştığını kanıtlayan en ucuz sorgu."""

from app.db import cursor


async def kontrol() -> dict:
    async with cursor() as cur:
        await cur.execute(
            """
            SELECT (SELECT count(*) FROM information_schema.tables
                     WHERE table_schema='public' AND table_type='BASE TABLE') AS tablo,
                   (SELECT count(*) FROM information_schema.views
                     WHERE table_schema='public')                             AS view,
                   (SELECT count(*) FROM staff WHERE is_active)               AS aktif_personel
            """
        )
        return await cur.fetchone()
