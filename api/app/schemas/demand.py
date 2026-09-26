"""E-06 İhtiyaç ekranı — iki sekme: haftalık görünüm + şablon."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.schedule import DayHeader


class DemandTotal(BaseModel):
    required_hours: float = Field(description="Minimum kadro saati: GENEL min_count × vardiya süresi")
    assigned_hours: float
    shortfall_count: int


class DemandDraft(BaseModel):
    id: int
    name: str
    is_published: bool
    is_reference_copy: bool = False


class Demand(BaseModel):
    period_label: str
    period_start: date
    period_end: date = Field(description="DIŞLAYICI")
    draft: DemandDraft | None = None
    total: DemandTotal
    days: list[DayHeader] = Field(description="Çizelgeyle aynı yapı — tek tanım, tek davranış")


class TemplateRow(BaseModel):
    id: int
    shift_code: str
    shift_name: str
    slot_code: str
    slot_label: str
    min_count: int
    competency_codes: list[str] = Field(default_factory=list)

    # Hangi kurala bağlı: "kaç kişi" satırda, "zorunlu mu" kuralda (migration 010)
    constraint_code: str | None = None
    catalog_code: str | None = None
    constraint_name: str | None = None
    is_hard: bool | None = None


class NeedTemplate(BaseModel):
    id: int
    code: str
    name: str
    rows: list[TemplateRow]


class TemplateRowCreate(BaseModel):
    shift_code: str = Field(description="GUNDUZ / GECE")
    slot_code: str = Field(min_length=1, max_length=30)
    min_count: int = Field(ge=1, le=50)
    competency_codes: list[str] = Field(default_factory=list)


class TemplateRowUpdate(BaseModel):
    min_count: int = Field(ge=1, le=50)
