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
    kullanici: str | None = Field(
        default=None, description="Veritabanına bağlanan rol — canlıda nobet_app olmalı"
    )
    tablo: int | None = None
    view: int | None = None
    aktif_personel: int | None = None
    sema_guncel: bool | None = Field(
        default=None,
        description="Veritabanı şeması deploy edilen kodun beklediği migration'ları içeriyor mu",
    )
    eksik_migration: str | None = Field(
        default=None, description="Veritabanında eksik olan migration'lar"
    )
    detay: str | None = None
