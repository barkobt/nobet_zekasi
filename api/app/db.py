"""Veritabanı havuzu. ORM yok: psycopg 3 + düz SQL, satırlar dict olarak gelir."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.settings import get_settings

_pool: AsyncConnectionPool | None = None


async def open_pool() -> AsyncConnectionPool:
    """Uygulama açılışında bir kez çağrılır (main.py lifespan)."""
    global _pool
    settings = get_settings()
    _pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=settings.db_pool_min,
        max_size=settings.db_pool_max,
        # Bağlantı havuzdan ÇIKARKEN sınanır: kopmuşsa atılır ve yenisi kurulur.
        # Neon uykudan dönerken ilk isteğin hata vermesinin çözümü budur —
        # kullanıcı hatayı görmez, yalnız ilk istek biraz uzun sürer.
        check=AsyncConnectionPool.check_connection,
        max_idle=settings.db_pool_max_idle,
        max_lifetime=settings.db_pool_max_lifetime,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await _pool.open(wait=True, timeout=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Veritabanı havuzu açık değil.")
    return _pool


@asynccontextmanager
async def cursor() -> AsyncIterator:
    """Repository'lerin tek giriş noktası: `async with cursor() as cur: ...`"""
    async with get_pool().connection() as conn, conn.cursor() as cur:
        yield cur
