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
    period_start: date
    period_end: date = Field(description="DIŞLAYICI bitiş: [başlangıç, bitiş)")
    day_count: int = Field(default=0, description="Aralıktaki gün sayısı")
    status: Literal["taslak", "yayinlandi", "arsiv"]
    unit_name: str
    created_at: datetime | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = Field(
        default=None,
        description="En son ne olduğu: yayınlanma, çözüm koşusu ya da atama yazımı. "
                    "Taslaklar listesindeki 'Son 7 gün / 30 gün / Eski' ölçütü bu.",
    )

    assignment_count: int = 0
    staff_count: int = Field(default=0, description="Ataması olan kişi sayısı")
    shortfall_count: int = Field(default=0, description="Kapsama eksiği olan slot sayısı")
    total_hours: float = 0.0
    overtime_hours: float = 0.0
    fairness_gap: float = Field(default=0.0, description="En çok − en az çalışan saat farkı")
    covers_full_month: bool = False
    last_run: SolverRun | None = None


class DraftCreate(BaseModel):
    period_start: date = Field(description="Başlangıç günü (dahil)")
    period_end: date = Field(description="Bitiş günü (DAHİL) — API dışlayıcıya çevirir")
    name: str = Field(min_length=1, max_length=100)
    unit_code: str = "ACIL_SERVIS"
    # Başlangıç verisi: boş / yayınlanmış atamalardan / referans haftadan
    seed_from: Literal["bos", "yayinlanmis", "referans"] = "bos"
    lock_seeded: bool = Field(
        default=False, description="Kopyalanan atamalar kilitlensin (solver dokunmaz)"
    )


class PublishPreview(BaseModel):
    """Uygulamadan ÖNCE ne olacağını söyler. Kullanıcı sürprizle karşılaşmasın."""

    can_publish: bool
    archived_names: list[str] = Field(
        default_factory=list, description="Arşive alınacak yayınlanmış çizelgeler"
    )
    uncovered_label: str | None = Field(
        default=None,
        description="Eskinin yeni taslağın dışında kalan günleri, insan diliyle",
    )
    manual_change_count: int = Field(
        default=0, description="Mevcut çizelgede elle yapılmış değişiklik sayısı"
    )
    reason: str | None = Field(default=None, description="Uygulanamıyorsa sebebi")


class DraftRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class DraftCopy(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SolveRequest(BaseModel):
    # None → sunucu ayarındaki SOLVER_TIME_LIMIT_S kullanılır (demo: 25 sn)
    time_limit_s: int | None = Field(default=None, ge=5, le=600)


class SolveAccepted(BaseModel):
    """POST /solve yanıtı: koşu kaydı açıldı, arka planda çalışıyor."""

    run_id: int
    draft_id: int
    status: RunStatus
    poll_url: str
    time_limit_s: int = Field(description="Arayüz geri sayımı buna göre gösterir")


class Diagnostic(BaseModel):
    id: int
    severity: Literal["hata", "cakisma", "ihlal", "uyari"]
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
    severity: str = Field(
        default="ihlal",
        description="Gruptaki en ağır seviye — 'hata' kontrolcünün bulduğu katı kural ihlalidir",
    )
    count: int
    first_date: date | None = None
    last_date: date | None = None
    samples: list[Diagnostic] = Field(default_factory=list, description="İlk birkaç örnek")
