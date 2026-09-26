"""E-08 Taslaklar + Çöz + E-10 Teşhis."""

import asyncio
from datetime import date, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.repositories import drafts as repo
from app.schemas.drafts import (
    Diagnostic, DiagnosticGroup, Draft, DraftCreate, SolveAccepted, SolveRequest, SolverRun,
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
    # Taslak ayın TAMAMINI kapsıyor mu? Aylık hedef karşılaştırması (C-004)
    # yalnızca bu doğruysa anlamlı; kısmi taslakta eksik görünmesi kuralın
    # ihlali değil verinin eksikliğidir.
    ay_bas: date = satir["month_start"]
    sonraki = date(ay_bas.year + (ay_bas.month == 12), ay_bas.month % 12 + 1, 1)
    ay_son = sonraki - timedelta(days=1)
    tam_ay = bool(
        satir["ilk_gun"]
        and satir["son_gun"]
        and satir["ilk_gun"] <= ay_bas
        and satir["son_gun"] >= ay_son
    )
    return Draft(
        id=satir["id"], name=satir["name"], month_start=ay_bas, status=satir["status"],
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
    try:
        yeni = await repo.olustur(istek.unit_code, istek.month_start, istek.name)
    except Exception as hata:  # noqa: BLE001 — DB kısıtlarını Türkçeye çevir
        metin = str(hata)
        if "ck_drafts_month_start" in metin:
            raise HTTPException(status_code=422, detail="Ay başlangıcı ayın ilk günü olmalı.") from hata
        raise HTTPException(status_code=422, detail="Taslak oluşturulamadı.") from hata
    if yeni is None:
        raise HTTPException(status_code=404, detail="Birim bulunamadı.")
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

    run_id = await repo.kosu_ac(draft_id, istek.time_limit_s)

    def calistir() -> None:
        # run_solver SENKRON ve kendi bağlantısını açar (CP-SAT bloklar).
        # to_thread ile olay döngüsü serbest kalır; yoklama istekleri yanıtlanabilir.
        from solver.interface import run_solver

        run_solver(draft_id=draft_id, time_limit_s=istek.time_limit_s)

    async def gorev() -> None:
        await asyncio.to_thread(calistir)

    arka_plan.add_task(gorev)
    return SolveAccepted(
        run_id=run_id, draft_id=draft_id, status="CALISIYOR",
        poll_url=f"/api/solver-runs/{run_id}",
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
