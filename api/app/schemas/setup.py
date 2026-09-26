"""E-02 Yetkinlik Matrisi · E-03 Kural Seti · E-01 Vardiya Tanımları."""

from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

CompetencyKind = Literal["TASK", "QUALIFICATION"]


class Competency(BaseModel):
    id: int
    code: str
    name: str
    kind: CompetencyKind
    description: str | None = None
    staff_count: int = Field(default=0, description="Sütun altı toplamı — fizibilite erken görünsün")


class MatrixRow(BaseModel):
    staff_id: int
    full_name: str
    role_name: str
    is_orientation: bool
    codes: list[str] = Field(default_factory=list, description="Sahip olduğu yetkinlik kodları")


class CompetencyMatrix(BaseModel):
    # Görev yetkinlikleri (TASK) diğerlerinden ayrı grupta gösterilir
    tasks: list[Competency]
    qualifications: list[Competency]
    rows: list[MatrixRow]


class ConstraintParam(BaseModel):
    id: int
    param_key: str
    param_value: float
    description: str | None = None


class Constraint(BaseModel):
    id: int
    code: str
    catalog_code: str | None = None
    name: str
    description: str | None = None
    is_hard: bool
    default_weight: int | None = Field(default=None, description="Soft kuralda pozitif, hard'da boş")
    scope: str
    scope_label: str
    source: str
    source_label: str
    locked: bool = Field(description="Kaynağı 'yasal' olanlar gevşetilemez")
    params: list[ConstraintParam] = Field(default_factory=list)


class ConstraintUpdate(BaseModel):
    is_hard: bool | None = None
    default_weight: int | None = Field(default=None, ge=1, le=1000)


class ParamUpdate(BaseModel):
    param_value: float = Field(ge=0)


class ShiftType(BaseModel):
    id: int
    code: str
    name: str
    start_time: time
    duration_hours: float
    end_label: str = Field(description="Bitiş saati, insan diliyle")
    crosses_midnight: bool
    is_active: bool
    unit_name: str
