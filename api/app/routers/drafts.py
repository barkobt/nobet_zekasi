"""E-08 Taslaklar + Çöz + E-10 Teşhis."""

import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.repositories import drafts as repo
from app.schemas.drafts import (
    Diagnostic, DiagnosticGroup, Draft, DraftCopy, DraftCreate, SolveAccepted,
    SolveRequest, SolverRun,
)
from app.settings import get_settings

router = APIRouter(tags=["taslaklar"])

# Stub gerçek bir çözücü değil; referans haftayı kopyalıyor. Arayüz bunu açıkça
# söylemezse "Çözüldü" ile hard kural eksikleri yan yana çelişkili görünür.
# model.py devreye girince params_snapshot'taki bayrak düşer, etiketler kaybolur.
_STUB_DURUM = "Referans kopya (solver değil)"
_STUB_TESHIS = "Kapsama eksikleri"

_DURUM_ADI = {
    "CALISIYOR": "Çalışıyor",
    "OPTIMAL": "En iyi çözüm",
    "FEASIBLE": "Çözüldü",
    "INFEASIBLE": "Çözülemedi",
    "HATA": "Hata",
}


def _kosu(satir: dict) -> SolverRun:
    stub = satir.get("solver_impl") == "stub"
    return SolverRun(
        id=satir["id"],
        draft_id=satir["draft_id"],
        status=satir["status"],
        started_at=satir["started_at"],
        finished_at=satir["finished_at"],
        time_limit_seconds=satir["time_limit_seconds"],
        objective_value=float(satir["objective_value"]) if satir["objective_value"] is not None else None,
        assignment_count=satir["assignment_count"],
        diagnostic_count=satir["diagnostic_count"],
        elapsed_s=round(float(satir["elapsed_s"]), 2) if satir["elapsed_s"] is not None else None,
        is_reference_copy=stub,
        status_label=(
            _STUB_DURUM if stub and satir["status"] in ("FEASIBLE", "OPTIMAL")
            else _DURUM_ADI.get(satir["status"], satir["status"])
        ),
        diagnostics_label=_STUB_TESHIS if stub else "Çözüm teşhisi",
    )


def _taslak(satir: dict, son_kosu: dict | None) -> Draft:
    # C-004 (aylık 200 saat) karşılaştırması: aralık tam bir takvim ayı olmalı
    # VE atamalar aralığı kapsamalı. Bkz. routers/schedule.py'deki aynı hesap.
    bas: date = satir["period_start"]
    bitis: date = satir["period_end"]          # DIŞLAYICI
    sonraki_ay = date(bas.year + (bas.month == 12), bas.month % 12 + 1, 1)
    tam_takvim_ayi = bas.day == 1 and bitis == sonraki_ay
    tam_ay = bool(
        tam_takvim_ayi
        and satir["ilk_gun"] and satir["son_gun"]
        and satir["ilk_gun"] <= bas
        and satir["son_gun"] >= bitis - timedelta(days=1)
    )
    return Draft(
        id=satir["id"], name=satir["name"],
        period_start=bas, period_end=bitis, day_count=(bitis - bas).days,
        status=satir["status"],
        unit_name=satir["unit_name"], created_at=satir["created_at"],
        published_at=satir["published_at"],
        assignment_count=satir["assignment_count"], staff_count=satir["staff_count"],
        shortfall_count=satir["shortfall_count"],
        total_hours=round(float(satir["total_hours"]), 1),
        overtime_hours=round(float(satir["overtime_hours"]), 1),
        fairness_gap=round(float(satir["fairness_gap"]), 1),
        covers_full_month=tam_ay,
        last_run=_kosu(son_kosu) if son_kosu else None,
    )


@router.get("/drafts", response_model=list[Draft], summary="Taslak listesi")
async def listele() -> list[Draft]:
    satirlar = await repo.listele()
    return [_taslak(s, await repo.son_kosu(s["id"])) for s in satirlar]


@router.post("/drafts", response_model=Draft, status_code=201, summary="Yeni taslak")
async def olustur(istek: DraftCreate) -> Draft:
    if istek.period_end < istek.period_start:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan önce olamaz.")
    try:
        # Kullanıcı KAPSAYICI bitiş seçer; veritabanı DIŞLAYICI tutar.
        yeni = await repo.olustur(
            istek.unit_code, istek.period_start, istek.period_end + timedelta(days=1), istek.name
        )
    except Exception as hata:  # noqa: BLE001 — DB kısıtlarını Türkçeye çevir
        metin = str(hata)
        if "ck_drafts_period_bounded" in metin:
            raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan sonra olmalı.") from hata
        if "ex_drafts_one_published" in metin:
            raise HTTPException(
                status_code=409,
                detail="Bu tarih aralığında zaten yayınlanmış bir çizelge var.",
            ) from hata
        raise HTTPException(status_code=422, detail="Taslak oluşturulamadı.") from hata
    if yeni is None:
        raise HTTPException(status_code=404, detail="Birim bulunamadı.")

    # Başlangıç verisi: istenirse mevcut bir çizelgeden doldur.
    if istek.seed_from != "bos":
        kaynak = await repo.kaynak_taslak_bul(
            istek.seed_from, istek.period_start, istek.period_end + timedelta(days=1)
        )
        if kaynak is not None:
            await repo.baslangic_verisi_kopyala(yeni["id"], kaynak, istek.lock_seeded)

    return await getir(yeni["id"])


@router.get("/drafts/{draft_id}", response_model=Draft, summary="Taslak detayı")
async def getir(draft_id: int) -> Draft:
    if (s := await repo.getir(draft_id)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")
    return _taslak(s, await repo.son_kosu(draft_id))


@router.post("/drafts/{draft_id}/solve", response_model=SolveAccepted, status_code=202,
             summary="Çöz — arka planda çalıştırır")
async def coz(draft_id: int, istek: SolveRequest, arka_plan: BackgroundTasks) -> SolveAccepted:
    if await repo.getir(draft_id) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")

    # Çift tıklama koruması: süren koşu varsa yenisini açma, mevcudu döndür.
    if (suren := await repo.calisan_kosu(draft_id)) is not None:
        return SolveAccepted(
            run_id=suren["id"], draft_id=draft_id, status="CALISIYOR",
            poll_url=f"/api/solver-runs/{suren['id']}",
        )

    sure = istek.time_limit_s or get_settings().solver_time_limit_s
    run_id = await repo.kosu_ac(draft_id, sure)

    def calistir() -> None:
        # run_solver SENKRON ve kendi bağlantısını açar (CP-SAT bloklar).
        # to_thread ile olay döngüsü serbest kalır; yoklama istekleri yanıtlanabilir.
        from solver.interface import run_solver

        run_solver(draft_id=draft_id, time_limit_s=sure)

    async def gorev() -> None:
        await asyncio.to_thread(calistir)

    arka_plan.add_task(gorev)
    return SolveAccepted(
        run_id=run_id, draft_id=draft_id, status="CALISIYOR",
        poll_url=f"/api/solver-runs/{run_id}", time_limit_s=sure,
    )


@router.get("/drafts/{draft_id}/runs", response_model=list[SolverRun], summary="Taslağın koşuları")
async def kosular(draft_id: int) -> list[SolverRun]:
    return [_kosu(s) for s in await repo.kosular(draft_id)]


@router.get("/solver-runs/{run_id}", response_model=SolverRun, summary="Koşu durumu (yoklama)")
async def kosu(run_id: int) -> SolverRun:
    if (s := await repo.kosu(run_id)) is None:
        raise HTTPException(status_code=404, detail="Koşu bulunamadı.")
    return _kosu(s)


@router.get("/solver-runs/{run_id}/diagnostics", response_model=list[DiagnosticGroup],
            summary="E-10 teşhisler, kurala göre gruplu")
async def teshisler(run_id: int) -> list[DiagnosticGroup]:
    if (k := await repo.kosu(run_id)) is None:
        raise HTTPException(status_code=404, detail="Koşu bulunamadı.")

    satirlar = await repo.teshisler(run_id)

    # Kurala göre grupla: 44 satır yerine 7 kalem. Ham liste örneklerde duruyor.
    gruplar: dict[str, DiagnosticGroup] = {}
    for s in satirlar:
        anahtar = s["constraint_code"] or "—"
        d = Diagnostic(
            id=s["id"], severity=s["severity"], constraint_code=s["constraint_code"],
            catalog_code=s["catalog_code"], constraint_name=s["constraint_name"],
            staff_name=s["staff_name"], work_date=s["work_date"],
            message=s["message"], suggestion=s["suggestion"],
        )
        g = gruplar.get(anahtar)
        if g is None:
            gruplar[anahtar] = DiagnosticGroup(
                catalog_code=s["catalog_code"], constraint_code=s["constraint_code"],
                constraint_name=s["constraint_name"] or "Bağlanmamış",
                count=1, first_date=s["work_date"], last_date=s["work_date"], samples=[d],
            )
        else:
            g.count += 1
            if s["work_date"]:
                g.first_date = min(g.first_date or s["work_date"], s["work_date"])
                g.last_date = max(g.last_date or s["work_date"], s["work_date"])
            if len(g.samples) < 3:
                g.samples.append(d)

    return sorted(gruplar.values(), key=lambda g: (-g.count, g.catalog_code or "zz"))


@router.delete("/drafts/{draft_id}", status_code=204, summary="Taslağı sil")
async def taslak_sil(
    draft_id: int,
    yayinlanmis_da_sil: bool = Query(
        default=False, alias="force",
        description="Yayınlanmış çizelgeyi silmek için açıkça istenmeli",
    ),
) -> None:
    """Atamalar, koşular ve teşhisler de gider (şemadaki ON DELETE CASCADE)."""
    if (d := await repo.durum(draft_id)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")
    # Yayınlanmış çizelge yürürlükteki nöbettir; tek tıkla gitmemeli.
    if d["status"] == "yayinlandi" and not yayinlanmis_da_sil:
        raise HTTPException(
            status_code=409,
            detail="Bu çizelge yayınlanmış. Silmek için önce yayından kaldırın "
                   "ya da silmeyi açıkça onaylayın.",
        )
    if await repo.sil(draft_id) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")


@router.post("/drafts/{draft_id}/copy", response_model=Draft, status_code=201,
             summary="Taslağı kopyala")
async def taslak_kopyala(draft_id: int, istek: DraftCopy) -> Draft:
    if (yeni := await repo.kopyala(draft_id, istek.name)) is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")
    return await getir(yeni["id"])


@router.post("/drafts/{draft_id}/publish", response_model=Draft, summary="Taslağı yayınla")
async def taslak_yayinla(draft_id: int) -> Draft:
    try:
        sonuc = await repo.yayinla(draft_id)
    except Exception as hata:  # noqa: BLE001
        if "ex_drafts_one_published" in str(hata):
            raise HTTPException(
                status_code=409,
                detail="Bu tarih aralığında zaten yayınlanmış bir çizelge var.",
            ) from hata
        raise HTTPException(status_code=422, detail="Taslak yayınlanamadı.") from hata
    if sonuc is None:
        raise HTTPException(status_code=404, detail="Taslak bulunamadı.")
    return await getir(draft_id)
