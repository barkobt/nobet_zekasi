"""Ana sayfa (E-00) — uygulama buradan açılır."""

from datetime import date, timedelta

from fastapi import APIRouter, Query

from app.repositories import overview as repo
from app.schemas.overview import Overview, OverviewDraft

router = APIRouter(tags=["ana sayfa"])

AY_ADI = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
KISA_AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def _etiket(bas: date, bitis: date) -> str:
    """bitis DIŞLAYICI. Tam ay → 'Ekim 2026', hafta → '5–11 Eki 2026'."""
    son = bitis - timedelta(days=1)
    sonraki_ay = date(bas.year + (bas.month == 12), bas.month % 12 + 1, 1)
    if bas.day == 1 and bitis == sonraki_ay:
        return f"{AY_ADI[bas.month - 1]} {bas.year}"
    if bas == son:
        return f"{bas.day} {KISA_AY[bas.month - 1]} {bas.year}"
    if bas.month == son.month and bas.year == son.year:
        return f"{bas.day}–{son.day} {KISA_AY[son.month - 1]} {son.year}"
    return f"{bas.day} {KISA_AY[bas.month - 1]} – {son.day} {KISA_AY[son.month - 1]} {son.year}"


@router.get("/overview", response_model=Overview, summary="Ana sayfa kartı")
async def ozet(
    gun_bas: date = Query(alias="from"),
    gun_son: date = Query(alias="to", description="DAHİL — API dışlayıcıya çevirir"),
) -> Overview:
    bitis = gun_son + timedelta(days=1)
    v = await repo.ozet(gun_bas, bitis)

    t = v["taslak"]
    return Overview(
        unit_name=v["birim"],
        period_start=gun_bas,
        period_end=bitis,
        period_label=_etiket(gun_bas, bitis),
        draft=OverviewDraft(
            id=t["id"], name=t["name"], status=t["status"],
            is_published=t["status"] == "yayinlandi",
        ) if t else None,
        assigned_hours=round(v["atanan"], 1),
        required_hours=round(v["gereken"], 1),
        coverage_ratio=round(v["atanan"] / v["gereken"], 3) if v["gereken"] else 0.0,
        violation_count=v["ihlal"],
        overtime_hours=round(v["fazla_mesai"], 1),
        fairness_gap=round(v["adalet"], 1),
    )
