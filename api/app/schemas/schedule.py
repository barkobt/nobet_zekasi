"""E-09 Nöbet Çizelgesi sözleşmesi.

Tek çağrı, üç parça: days (sütun başlıkları), groups (satırlar), summary (alt bar).
Ekranın tamamı bu yanıttan çizilir; frontend ikinci bir istek atmaz.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class SlotCoverage(BaseModel):
    """Bir gün-vardiya içindeki tek slotun durumu. Sütun başlığı tooltip'inde gösterilir."""

    slot_code: str
    label: str
    assigned: int
    required: int
    qualified: int | None = Field(
        default=None,
        description="O vardiyada slotun yetkinliğine SAHİP kişi sayısı (rozetten bağımsız)",
    )
    remaining_after_ambulance: int | None = Field(
        default=None,
        description="TRIYAJ/GOZLEM: ambulansa çıkmayanların sayısı. Diğer slotlarda boş.",
    )


class ShiftHeader(BaseModel):
    """Gün başlığındaki tek vardiya sayacı: DESIGN §6 'G 6/6' ve 'N 5/5'.

    assigned/required YALNIZCA genel mevcut (GENEL slotu), kişi sayısı — saat değil.
    Slot kırılımı `slots` içinde, tooltip'e gider; başlık sayacını etkilemez.
    """

    code: str
    label: Literal["G", "N"]
    assigned: int
    required: int
    slots: list[SlotCoverage] = Field(default_factory=list)


class DayHeader(BaseModel):
    day: date
    weekday: str = Field(description="Pzt, Sal, …")
    label: str = Field(description="Gün + kısa ay, örn. '21 Eyl'")
    is_weekend: bool
    shifts: list[ShiftHeader]


class Cell(BaseModel):
    """Bir kişinin bir günü. Vardiya yoksa hücre hiç gönderilmez."""

    shift_code: str
    shift_label: Literal["G", "N"]
    tasks: list[str] = Field(default_factory=list, description="Görev kodları: TRIYAJ, AMBULANS, GOZLEM")
    is_locked: bool = False
    source: str


class Row(BaseModel):
    staff_id: int
    full_name: str
    role_name: str
    is_orientation: bool
    initials: str
    cells: dict[str, Cell] = Field(description="ISO tarih → hücre; çalışılmayan gün anahtarı yok")
    absences: dict[str, str] = Field(default_factory=dict, description="ISO tarih → izin türü")
    month_hours: float = Field(description="Taslağın ayındaki toplam planlanan saat")
    month_target: float
    month_diff: float = Field(description="Hedefe göre fark: pozitif fazla, negatif eksik")
    shift_count: int


class Group(BaseModel):
    """DESIGN §6: rol grubuna göre katlanabilir bölümler."""

    key: str
    label: str
    rows: list[Row]


class Summary(BaseModel):
    """DESIGN §6 alt barı."""

    total_hours: float
    overtime_hours: float
    fairness_gap: float = Field(description="Kişiler arası saat farkı: en çok − en az")
    shortfall_count: int = Field(description="Seçili aralıkta eksik kalan slot sayısı")


class DraftInfo(BaseModel):
    id: int
    name: str
    month_start: date
    status: str
    unit_name: str
    covers_full_month: bool = Field(
        description="Atamalar ayın tamamına yayılıyor mu? Aylık hedef karşılaştırması "
                    "(C-004) yalnızca bu doğruysa anlamlıdır."
    )


class Schedule(BaseModel):
    draft: DraftInfo
    days: list[DayHeader]
    groups: list[Group]
    summary: Summary
    notes: list[str] = Field(default_factory=list, description="Izgaranın altındaki açıklama satırları")
