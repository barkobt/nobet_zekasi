"""Raporlar ekranının sözleşmesi. Hesaplar app/rapor.py'de, burada yalnız biçim."""

from datetime import date

from pydantic import BaseModel, Field


class PersonSummary(BaseModel):
    staff_id: int
    full_name: str
    role_name: str
    total_hours: float
    night_count: int
    weekend_count: int
    target_hours: float | None = Field(
        description="Tam ay → 200, tam hafta → 45; başka dönemde null (orantı yapılmaz)"
    )
    diff_hours: float | None
    gross_hours: float = Field(
        0, description="Dönemin BRÜT (molalar dahil) saati — net ile aynı kapsam"
    )
    overtime_hours: float = Field(
        0, description="Fazla mesai: haftalık brüt 51 sa üstünün toplamı (O-001)"
    )


class Shortfall(BaseModel):
    day: date
    shift_code: str
    shift_name: str
    slot_code: str
    slot_name: str
    assigned: int
    required: int
    missing: int


class Report(BaseModel):
    draft_id: int
    draft_name: str
    unit_name: str
    status: str
    period_start: date
    period_end: date = Field(description="DIŞLAYICI bitiş")
    period_label: str
    target_note: str | None
    people: list[PersonSummary]
    shortfalls: list[Shortfall]
