"""Ayarlar ekranının verisi: görünür sayaçlar, kullanıcı tercihleri, kurum ayarları.

Üçü ayrı tabloda durur ve anlamları farklıdır:
  * visible_counters → kurum geneli, hangi sayaç hangi görünümde çıkar
  * app_preferences  → KULLANICI başına arayüz tercihi
  * app_settings     → kuruma ait tek değerli metin ayarları (örn. kurum adı)
"""

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


# ------------------------------------------------------------ kurum ayarları ---

_AYARLAR = """
SELECT key, value, label, description
FROM app_settings
ORDER BY key
"""


async def ayarlar() -> list[dict]:
    async with cursor() as cur:
        await cur.execute(_AYARLAR)
        return await cur.fetchall()


async def ayar(key: str) -> dict | None:
    async with cursor() as cur:
        await cur.execute(
            "SELECT key, value, label, description FROM app_settings WHERE key = %s",
            (key,),
        )
        return await cur.fetchone()


async def ayar_yaz(key: str, value: str) -> dict | None:
    """Var olan ayarı günceller. Anahtar yoksa None döner — yeni ayar arayüzden
    AÇILMAZ, çünkü her ayarın kodda onu okuyan bir yeri olmalı."""
    async with cursor() as cur:
        await cur.execute(
            """UPDATE app_settings
                  SET value = %s, updated_at = CURRENT_TIMESTAMP
                WHERE key = %s
            RETURNING key, value, label, description""",
            (value, key),
        )
        return await cur.fetchone()
