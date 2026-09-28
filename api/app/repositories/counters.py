"""Görünür sayaç ayarları ve kullanıcı tercihleri (app_preferences)."""

from typing import Any

from psycopg.types.json import Jsonb

from app.db import cursor

_SAYACLAR = """
SELECT key, badge, label, description, always_shown, weekly_on, monthly_on
FROM visible_counters
ORDER BY sort_order
"""


async def sayaclar() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_SAYACLAR)
        return await cur.fetchall()


async def sayaclari_yaz(degisiklikler: list[tuple[str, bool, bool]]) -> int:
    """Toplu kaydet. always_shown olanlar CHECK ile korunuyor; onları hiç göndermeyiz."""
    if not degisiklikler:
        return 0
    async with cursor() as cur:
        await cur.executemany(
            """UPDATE visible_counters
                  SET weekly_on = %s, monthly_on = %s, updated_at = CURRENT_TIMESTAMP
                WHERE key = %s AND NOT always_shown""",
            [(h, a, k) for k, h, a in degisiklikler],
        )
        return cur.rowcount


async def tercih(user_key: str, pref_key: str) -> Any | None:
    async with cursor() as cur:
        await cur.execute(
            "SELECT value FROM app_preferences WHERE user_key = %s AND pref_key = %s",
            (user_key, pref_key),
        )
        satir = await cur.fetchone()
        return None if satir is None else satir["value"]


async def tercih_yaz(user_key: str, pref_key: str, value: Any) -> None:
    async with cursor() as cur:
        await cur.execute(
            """INSERT INTO app_preferences (user_key, pref_key, value)
               VALUES (%s, %s, %s)
               ON CONFLICT (user_key, pref_key)
               DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP""",
            (user_key, pref_key, Jsonb(value)),
        )
