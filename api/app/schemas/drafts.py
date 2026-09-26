"""E-08 Taslaklar + solver çalıştırma sözleşmesi."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

RunStatus = Literal["CALISIYOR", "OPTIMAL", "FEASIBLE", "INFEASIBLE", "HATA"]


class SolverRun(BaseModel):
    """Bir çözüm koşusu. E-08 metrik tablosu ve durum yoklaması bunu okur."""

    id: int
    draft_id: int
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    time_limit_seconds: int | None = None
    objective_value: float | None = None
    assignment_count: int = 0
    diagnostic_count: int = 0
    elapsed_s: float | None = None

    # Dürüstlük etiketleri: stub gerçek bir çözücü değil, referans haftayı kopyalıyor.
    # params_snapshot->>'solver' = 'stub' olduğunda arayüz bunu açıkça söylemeli,
    # yoksa "Çözüldü" ile "hard kural eksikleri" yan yana çelişkili görünür.
    # model.py devreye girince bayrak kendiliğinden düşer, etiketler kaybolur.
    is_reference_copy: bool = Field(
        default=False, description="Gerçek çözücü değil, referans haftanın kopyası"
    )
    status_label: str = Field(description="Arayüzde gösterilecek durum metni")
    diagnostics_label: str = Field(description="Teşhis listesinin başlığı")


class Draft(BaseModel):
    id: int
    name: str
    month_start: date
    status: Literal["taslak", "yayinlandi", "arsiv"]
    unit_name: str
    created_at: datetime | None = None
    published_at: datetime | None = None

    assignment_count: int = 0
    staff_count: int = Field(default=0, description="Ataması olan kişi sayısı")
    shortfall_count: int = Field(default=0, description="Kapsama eksiği olan slot sayısı")
    total_hours: float = 0.0
    overtime_hours: float = 0.0
    fairness_gap: float = Field(default=0.0, description="En çok − en az çalışan saat farkı")
    covers_full_month: bool = False
    last_run: SolverRun | None = None


class DraftCreate(BaseModel):
    month_start: date = Field(description="Ayın ilk günü, örn. 2026-10-01")
    name: str = Field(min_length=1, max_length=100)
    unit_code: str = "ACIL_SERVIS"


class SolveRequest(BaseModel):
    time_limit_s: int = Field(default=60, ge=5, le=600)


class SolveAccepted(BaseModel):
    """POST /solve yanıtı: koşu kaydı açıldı, arka planda çalışıyor."""

    run_id: int
    draft_id: int
    status: RunStatus
    poll_url: str


class Diagnostic(BaseModel):
    id: int
    severity: Literal["cakisma", "ihlal", "uyari"]
    constraint_code: str | None = None
    catalog_code: str | None = None
    constraint_name: str | None = None
    staff_name: str | None = None
    work_date: date | None = None
    message: str
    suggestion: str | None = None


class DiagnosticGroup(BaseModel):
    """E-10: teşhisler kurala göre gruplanır — 44 satır yerine 7 kalem."""

    catalog_code: str | None = None
    constraint_code: str | None = None
    constraint_name: str
    count: int
    first_date: date | None = None
    last_date: date | None = None
    samples: list[Diagnostic] = Field(default_factory=list, description="İlk birkaç örnek")
