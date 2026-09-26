"""Ortam ayarları — tek kaynak. Gizli değerler .env'de, .env.example commit edilir."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neon'da pooled bağlantı + sslmode=require, yerelde sade bir URL.
    database_url: str = "postgresql://localhost/nobet_zekasi"

    # Havuz: Railway'de tek süreç, Neon pooled tarafında cömert davranmaya gerek yok.
    db_pool_min: int = 1
    db_pool_max: int = 10

    # Hangi solver çağrılacak. model.py bitene kadar 'stub'.
    solver_impl: Literal["stub", "cpsat"] = "stub"
    # Demo ayarı: yöneticiler 25 saniyeden uzun beklemesin.
    solver_time_limit_s: int = 25

    # Web'in sunucu tarafı proxy'si bu token'ı gönderir; tarayıcıya hiç inmez.
    # Boş bırakılırsa doğrulama kapalıdır (yerel geliştirme).
    demo_api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
