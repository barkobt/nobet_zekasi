"""Ana sayfa (E-00) sözleşmesi — ortada tek kart."""

from datetime import date

from pydantic import BaseModel, Field


class OverviewDraft(BaseModel):
    id: int
    name: str
    status: str
    is_published: bool = Field(description="Yayınlanmış mı, yoksa yalnızca taslak mı")
    is_reference_copy: bool = Field(
        default=False,
        description="Son çalıştırma stub mı? Diğer ekranlardaki etiketlerle tutarlı olsun diye.",
    )


class Overview(BaseModel):
    unit_name: str
    period_start: date
    period_end: date = Field(description="DIŞLAYICI bitiş")
    period_label: str
    draft: OverviewDraft | None = None

    assigned_hours: float = Field(description="Dönemdeki atamaların toplam planlanan saati")
    required_hours: float = Field(
        description="İhtiyaç şablonundan türetilen gereken saat: "
                    "her gün, her vardiya için GENEL min_count × vardiya süresi"
    )
    coverage_ratio: float = Field(description="assigned / required, 0 ise 0")

    violation_count: int = Field(description="Kapsama eksiği olan gün-vardiya-slot sayısı")
    violation_label: str = Field(description="Stub'da 'Kapsama eksiği', gerçek çözümde 'Kural ihlali'")

    # Stub referans haftayı kopyalıyor; fazla mesai ve adalet farkı bir ÇÖZÜMÜN
    # kalitesini ölçer. Kopyada bu sayılar bir şey anlatmaz → None, arayüz "—" yazar.
    overtime_hours: float | None = None
    fairness_gap: float | None = Field(default=None, description="En çok − en az çalışan saat farkı")
