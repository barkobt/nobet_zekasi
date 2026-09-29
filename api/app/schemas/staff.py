"""API sözleşmesi — yalnızca biçim. openapi-typescript bu tanımlardan tip üretir."""

from typing import Literal

from pydantic import BaseModel, Field

ShiftEligibility = Literal["gunduz_gece", "sadece_gunduz", "sadece_gece"]


class Staff(BaseModel):
    id: int
    full_name: str = Field(description="Ad soyad")
    role_code: str
    role_name: str
    shift_eligibility: ShiftEligibility
    is_orientation: bool
    is_active: bool
    seniority_years: float | None = None
    buddy_name: str | None = Field(default=None, description="Oryantasyondaysa eşleştiği eğitim hemşiresi")
    note: str | None = None
    competency_codes: list[str] = Field(default_factory=list, description="Tüm yetkinlikler")
    task_codes: list[str] = Field(default_factory=list, description="Yalnızca görev (kind=TASK) olabilecekler")


class HealthCheck(BaseModel):
    status: Literal["ok", "hata"]
    db: bool
    cekirdek: int | None = Field(
        default=None, description="Sunucunun gördüğü CPU çekirdeği — çözüm kalitesini belirler"
    )
    solver_isci: int | None = Field(
        default=None, description="SOLVER_WORKERS ayarı; çekirdekten fazlası fayda etmez"
    )
    kullanici: str | None = Field(
        default=None, description="Veritabanına bağlanan rol — canlıda nobet_app olmalı"
    )
    tablo: int | None = None
    view: int | None = None
    aktif_personel: int | None = None
    okunamayan_tablo: int | None = Field(
        default=None,
        description="Bağlanan rolün SELECT yapamadığı tablo sayısı. 0 olmalı; "
                    "sıfırdan büyükse migration başka bir rolle koştu ve GRANT unutuldu.",
    )
    sema_guncel: bool | None = Field(
        default=None,
        description="Veritabanı şeması deploy edilen kodun beklediği migration'ları içeriyor mu",
    )
    eksik_migration: str | None = Field(
        default=None, description="Veritabanında eksik olan migration'lar"
    )
    detay: str | None = None
