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
    # Adım 5 ölçümü: adalet katmanıyla çözüm kalitesi ~30 sn'de platoya oturuyor
    # ama optimallik kanıtlanmıyor. 60 sn'de plato her koşuda yakalanıyor;
    # 25 sn'de üç koşudan birinde daha dengesiz bir çizelge çıkıyordu.
    solver_time_limit_s: int = 60

    # CP-SAT işçi sayısı. Çekirdekten FAZLA işçi çözümü hızlandırmaz, yavaşlatır:
    # işçiler aynı çekirdek için yarışır. Railway'in verdiği vCPU'ya göre ayarlanır.
    solver_workers: int = 8

    # Aynı anda kaç taslak çözülebilir. Her çözüm solver_workers kadar iş parçacığı
    # tutar; sınırsız bırakılırsa birkaç eşzamanlı istek API'yi yanıt veremez hale
    # getirir. 1 = kuyruk yok, ikinci istek "meşgul" yanıtı alır.
    solver_max_concurrent: int = 1

    # Ortam adı. 'production' iken /docs, /redoc ve /openapi.json kapatılır:
    # API yüzeyinin tamamını internete açık bırakmanın gereği yok.
    environment: str = "development"

    @property
    def uretim_mi(self) -> bool:
        return self.environment.lower() in ("production", "prod")

    # Web'in sunucu tarafı proxy'si bu token'ı gönderir; tarayıcıya hiç inmez.
    # Boş bırakılırsa doğrulama kapalıdır (yerel geliştirme).
    demo_api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
