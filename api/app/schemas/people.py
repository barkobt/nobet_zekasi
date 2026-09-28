"""E-04 Personel — liste + sekmeli detay."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

ShiftEligibility = Literal["gunduz_gece", "sadece_gunduz", "sadece_gece"]
AbsenceType = Literal["yillik_izin", "rapor", "ucretsiz_izin", "diger"]
RuleType = Literal["BOS_GUN", "SADECE_GUNDUZ", "SADECE_GECE"]
RuleStrength = Literal["KESIN", "MUMKUNSE"]


class Contract(BaseModel):
    id: int
    valid_from: date
    valid_to: date | None = Field(default=None, description="Açık uçluysa boş")
    monthly_target_hours: float | None = Field(
        default=None, description="Boşsa kural varsayılanı (monthly_min_hours) geçerli"
    )
    note: str | None = None


class Absence(BaseModel):
    id: int
    start: date
    end: date = Field(description="DAHİL")
    absence_type: AbsenceType
    type_label: str
    note: str | None = None


class AvailabilityRule(BaseModel):
    """Bir gün için istek. KESIN katı kuraldır, MUMKUNSE cezalandırılan tercihtir."""

    id: int
    target_date: date
    rule_type: RuleType
    type_label: str
    strength: RuleStrength
    strength_label: str
    summary: str = Field(description="Listede görünen özet: '17 Eki 2026 » Boş gün'")
    created_at: datetime | None = None
    note: str | None = None


class StaffCompetency(BaseModel):
    """Yetkinlik kataloğunun bir satırı + bu kişide var mı.

    TASK = ızgarada rozet olan görevler (triyaj, gözlem, ambulans),
    QUALIFICATION = rozetsiz yetkiler (ekip lideri, sayım, IV, İM, hasta iletişimi).
    """

    code: str
    name: str
    kind: Literal["TASK", "QUALIFICATION"]
    group_label: str = Field(description="'Görevler' / 'Yetkiler'")
    has: bool


class Conflict(BaseModel):
    other_staff_id: int
    other_name: str
    note: str | None = None


class PersonRow(BaseModel):
    """Liste satırı. Yetkinlik rozeti YOK — o E-02'de (26.09 kararı)."""

    id: int
    sicil_no: str | None = Field(default=None, description="Boşsa boş gösterilir, uydurulmaz")
    first_name: str
    last_name: str
    full_name: str
    role_code: str
    role_name: str
    display_group: str = Field(description="Listede ve ızgarada toplandığı grup (roles tablosundan)")
    group_order: int = Field(description="Grup içi sıra")
    shift_eligibility: ShiftEligibility
    eligibility_label: str
    monthly_target_hours: float | None = Field(
        default=None, description="Etkin aylık hedef: sözleşmedeki değer, yoksa kural varsayılanı"
    )
    target_is_default: bool = Field(
        default=False, description="Hedef sözleşmeden değil kuraldan geliyorsa true"
    )
    contract_label: str | None = Field(default=None, description="Sözleşme aralığı, insan diliyle")
    is_active: bool
    is_orientation: bool
    buddy_name: str | None = None
    status_label: str = Field(description="Oryantasyon / Pasif / boş")


class PersonDetail(PersonRow):
    buddy_staff_id: int | None = None
    assignment_count: int = Field(
        default=0, description="Kaç atamada geçiyor — silinebilir mi, pasife mi alınmalı"
    )
    can_delete: bool = Field(default=True, description="Ataması yoksa gerçekten silinebilir")
    seniority_years: float | None = None
    note: str | None = None
    competencies: list[StaffCompetency] = Field(
        default_factory=list, description="Katalogun TAMAMI; has=true olanlar kişide var"
    )
    contracts: list[Contract] = Field(default_factory=list)
    absences: list[Absence] = Field(default_factory=list)
    availability: list[AvailabilityRule] = Field(default_factory=list)
    conflicts: list[Conflict] = Field(default_factory=list)


class PersonCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    role_code: str
    shift_eligibility: ShiftEligibility = "gunduz_gece"
    sicil_no: str | None = None
    seniority_years: float | None = None
    note: str | None = None


class PersonUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    role_code: str | None = None
    shift_eligibility: ShiftEligibility | None = None
    sicil_no: str | None = None
    seniority_years: float | None = None
    note: str | None = None
    is_active: bool | None = None
    is_orientation: bool | None = None
    buddy_staff_id: int | None = Field(
        default=None, description="Oryantasyondaysa eğitmen. Şema kuralı: oryantasyon → eğitmen zorunlu."
    )


class ContractUpsert(BaseModel):
    valid_from: date
    valid_to: date | None = None
    monthly_target_hours: float | None = Field(default=None, gt=0)
    note: str | None = None


class AbsenceCreate(BaseModel):
    start: date
    end: date = Field(description="DAHİL")
    absence_type: AbsenceType
    note: str | None = None


class AvailabilityCreate(BaseModel):
    """Tek gün ya da aralık. `end` verilirse aralıktaki her güne bir istek yazılır."""

    target_date: date
    end_date: date | None = Field(default=None, description="Verilirse aralık (DAHİL)")
    rule_type: RuleType
    strength: RuleStrength = "MUMKUNSE"
    note: str | None = None


class AvailabilityUpdate(BaseModel):
    rule_type: RuleType | None = None
    strength: RuleStrength | None = None
    note: str | None = None


class CompetencyAssignment(BaseModel):
    """Kişinin yetkinlik listesi — tümü birden yazılır (eksikler silinir)."""

    codes: list[str]


class ConflictCreate(BaseModel):
    other_staff_id: int
    note: str | None = None


class Role(BaseModel):
    code: str
    name: str


class DeleteResult(BaseModel):
    """Silme mi oldu, pasife mi alındı — arayüz doğru mesajı gösterebilsin."""

    deleted: bool
    deactivated: bool
    message: str
