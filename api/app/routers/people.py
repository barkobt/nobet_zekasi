"""E-04 Personel — liste, detay, düzenleme."""

from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.repositories import people as repo
from app.schemas.people import (
    Absence, AbsenceCreate, AvailabilityCreate, AvailabilityRule, Conflict, ConflictCreate,
    Contract, ContractUpsert, DeleteResult, PersonCreate, PersonDetail, PersonRow,
    PersonUpdate, Role,
)

router = APIRouter(prefix="/people", tags=["personel"])

CALISMA_TIPI = {
    "gunduz_gece": "Gündüz + Gece",
    "sadece_gunduz": "Yalnız gündüz",
    "sadece_gece": "Yalnız gece",
}
IZIN_ADI = {
    "yillik_izin": "Yıllık izin", "rapor": "Rapor",
    "ucretsiz_izin": "Ücretsiz izin", "diger": "Diğer",
}
MUSAITLIK_ADI = {
    "off_talebi": "İzin talebi", "acilis_tercihi": "Açılış tercihi",
    "kapanis_tercihi": "Kapanış tercihi",
}
KISA_AY = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def _tarih(d: date) -> str:
    return f"{d.day} {KISA_AY[d.month - 1]} {d.year}"


def _ad_soyad(full_name: str) -> tuple[str, str]:
    """Son boşluktan böl. Şemada tek alan var; ayrıntı repositories/people.py'de."""
    parcalar = full_name.rsplit(" ", 1)
    return (parcalar[0], parcalar[1]) if len(parcalar) == 2 else (full_name, "")


def _satir(s: dict) -> PersonRow:
    ad, soyad = _ad_soyad(s["full_name"])
    donem = s.get("contract_period")
    sozlesme = None
    if donem is not None:
        bas = _tarih(donem.lower)
        sozlesme = f"{bas} – {_tarih(donem.upper - timedelta(days=1))}" if donem.upper else f"{bas} →"

    # İkisi birden olabilir: pasif bir oryantasyon personelinde "Pasif" kaybolmasın.
    etiketler = []
    if not s["is_active"]:
        etiketler.append("Pasif")
    if s["is_orientation"]:
        etiketler.append("Oryantasyon")
    durum = " · ".join(etiketler)
    return PersonRow(
        id=s["id"], sicil_no=s["sicil_no"], first_name=ad, last_name=soyad,
        full_name=s["full_name"], role_code=s["role_code"], role_name=s["role_name"],
        shift_eligibility=s["shift_eligibility"],
        eligibility_label=CALISMA_TIPI.get(s["shift_eligibility"], s["shift_eligibility"]),
        # "is not None" — falsy kontrolü 0'ı yok sayıyordu; 0 kıdem ya da
        # 0 hedef saat gerçek bir değer olabilir.
        monthly_target_hours=(
            float(s["monthly_target_hours"]) if s["monthly_target_hours"] is not None
            else (float(s["kural_hedefi"]) if s.get("kural_hedefi") is not None else None)
        ),
        target_is_default=s["monthly_target_hours"] is None,
        contract_label=sozlesme, is_active=s["is_active"], is_orientation=s["is_orientation"],
        buddy_name=s["buddy_name"], status_label=durum,
    )


@router.get("", response_model=list[PersonRow], summary="Personel listesi")
async def listele(
    q: str | None = Query(default=None, description="Ad veya sicilde arama"),
    durum: Literal["aktif", "pasif", "hepsi"] = Query(default="aktif"),
) -> list[PersonRow]:
    return [_satir(s) for s in await repo.listele(arama=q, durum=durum)]


@router.get("/roles", response_model=list[Role], summary="Rol listesi")
async def roller() -> list[Role]:
    return [Role(**r) for r in await repo.roller()]


@router.get("/{staff_id}", response_model=PersonDetail, summary="Personel detayı")
async def detay(staff_id: int) -> PersonDetail:
    if (s := await repo.getir(staff_id)) is None:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    d = await repo.detay(staff_id)

    return PersonDetail(
        **_satir(s).model_dump(),
        buddy_staff_id=s["buddy_staff_id"],
        assignment_count=s["assignment_count"],
        can_delete=s["assignment_count"] == 0,
        seniority_years=float(s["seniority_years"]) if s["seniority_years"] is not None else None,
        note=s["note"],
        contracts=[
            Contract(
                id=c["id"], valid_from=c["valid_from"],
                valid_to=c["valid_to"] - timedelta(days=1) if c["valid_to"] else None,
                monthly_target_hours=(
                    float(c["monthly_target_hours"]) if c["monthly_target_hours"] is not None else None
                ),
                note=c["note"],
            ) for c in d["sozlesmeler"]
        ],
        absences=[
            Absence(
                id=a["id"], start=a["bas"], end=a["bitis"] - timedelta(days=1),
                absence_type=a["absence_type"],
                type_label=IZIN_ADI.get(a["absence_type"], a["absence_type"]), note=a["note"],
            ) for a in d["izinler"]
        ],
        availability=[
            AvailabilityRule(
                id=m["id"], target_date=m["target_date"], rule_type=m["rule_type"],
                type_label=MUSAITLIK_ADI.get(m["rule_type"], m["rule_type"]), note=m["note"],
            ) for m in d["musaitlik"]
        ],
        conflicts=[Conflict(**u) for u in d["uyumsuzluk"]],
    )


@router.post("", response_model=PersonDetail, status_code=201, summary="Personel ekle")
async def olustur(istek: PersonCreate) -> PersonDetail:
    ad = f"{istek.first_name.strip()} {istek.last_name.strip()}".strip()
    try:
        yeni = await repo.olustur(ad, istek.role_code, istek.shift_eligibility,
                                  istek.sicil_no or None, istek.seniority_years, istek.note)
    except Exception as hata:  # noqa: BLE001 — DB kısıtını Türkçeye çevir
        if "uq_staff_sicil_no" in str(hata):
            raise HTTPException(status_code=409, detail="Bu sicil numarası zaten kayıtlı.") from hata
        raise HTTPException(status_code=422, detail="Personel eklenemedi.") from hata
    if yeni is None:
        raise HTTPException(status_code=422, detail="Rol bulunamadı.")
    return await detay(yeni["id"])


@router.patch("/{staff_id}", response_model=PersonDetail, summary="Personel düzenle")
async def guncelle(staff_id: int, istek: PersonUpdate) -> PersonDetail:
    if (mevcut := await repo.getir(staff_id)) is None:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")

    alanlar = istek.model_dump(exclude_unset=True)
    # Boş sicil NULL olmalı: '' olarak yazılırsa ikinci boş sicil UNIQUE'e takılıp
    # "bu sicil zaten kayıtlı" diyordu — ikisi de aslında boştu.
    if alanlar.get("sicil_no") == "":
        alanlar["sicil_no"] = None
    # Ad/soyad tek alanda saklanıyor: ikisinden biri gelse de tam adı yeniden kur.
    if "first_name" in alanlar or "last_name" in alanlar:
        eski_ad, eski_soyad = _ad_soyad(mevcut["full_name"])
        ad = alanlar.pop("first_name", eski_ad)
        soyad = alanlar.pop("last_name", eski_soyad)
        alanlar["full_name"] = f"{ad.strip()} {soyad.strip()}".strip()

    # Şema kuralı (ck_staff_orientation_buddy): oryantasyondaysa eğitmen zorunlu.
    # Hatayı veritabanından beklemek yerine burada anlaşılır biçimde söylüyoruz.
    hedef_ory = alanlar.get("is_orientation", mevcut["is_orientation"])
    hedef_buddy = alanlar.get("buddy_staff_id", mevcut["buddy_staff_id"])
    if hedef_ory and not hedef_buddy:
        raise HTTPException(status_code=422, detail="Oryantasyondaki personel için eğitmen seçin.")
    if hedef_buddy == staff_id:
        raise HTTPException(status_code=422, detail="Kişi kendi eğitmeni olamaz.")
    if not hedef_ory and "is_orientation" in alanlar:
        alanlar["buddy_staff_id"] = None   # oryantasyon bitince eğitmen bağı da düşer

    try:
        await repo.guncelle(staff_id, alanlar)
    except Exception as hata:  # noqa: BLE001
        if "uq_staff_sicil_no" in str(hata):
            raise HTTPException(status_code=409, detail="Bu sicil numarası zaten kayıtlı.") from hata
        raise HTTPException(status_code=422, detail="Personel güncellenemedi.") from hata
    return await detay(staff_id)


@router.delete("/{staff_id}", response_model=DeleteResult, summary="Personeli sil veya pasife al")
async def sil(staff_id: int) -> DeleteResult:
    """Ataması olan personel silinmez, pasife alınır.

    Veritabanı da buna zorluyor (fk_assignments_staff RESTRICT): geçmiş çizelgeler
    korunmalı. Pasif kişi listelerden ve solver'dan düşer ama kaydı durur.
    """
    if (s := await repo.getir(staff_id)) is None:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")

    if s["assignment_count"] > 0:
        await repo.guncelle(staff_id, {"is_active": False})
        return DeleteResult(
            deleted=False, deactivated=True,
            message=f"{s['full_name']} pasife alındı. "
                    f"{s['assignment_count']} atamada geçtiği için kaydı silinmedi.",
        )

    if not await repo.sil(staff_id):
        raise HTTPException(status_code=409, detail="Personel silinemedi.")
    return DeleteResult(deleted=True, deactivated=False, message=f"{s['full_name']} silindi.")


@router.post("/{staff_id}/activate", response_model=PersonDetail, summary="Pasif personeli aktife al")
async def aktife_al(staff_id: int) -> PersonDetail:
    if await repo.getir(staff_id) is None:
        raise HTTPException(status_code=404, detail="Personel bulunamadı.")
    await repo.guncelle(staff_id, {"is_active": True})
    return await detay(staff_id)


@router.post("/{staff_id}/contracts", response_model=PersonDetail, status_code=201,
             summary="Sözleşme ekle")
async def sozlesme_ekle(staff_id: int, istek: ContractUpsert) -> PersonDetail:
    try:
        await repo.sozlesme_ekle(
            staff_id, istek.valid_from,
            istek.valid_to + timedelta(days=1) if istek.valid_to else None,
            istek.monthly_target_hours, istek.note,
        )
    except Exception as hata:  # noqa: BLE001
        if "ex_contracts_no_overlap" in str(hata):
            raise HTTPException(
                status_code=409, detail="Bu tarihlerde zaten bir sözleşme var."
            ) from hata
        raise HTTPException(status_code=422, detail="Sözleşme eklenemedi.") from hata
    return await detay(staff_id)


@router.post("/{staff_id}/absences", response_model=PersonDetail, status_code=201,
             summary="Devamsızlık ekle")
async def izin_ekle(staff_id: int, istek: AbsenceCreate) -> PersonDetail:
    if istek.end < istek.start:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan önce olamaz.")
    try:
        await repo.izin_ekle(staff_id, istek.start, istek.end, istek.absence_type, istek.note)
    except Exception as hata:  # noqa: BLE001
        if "ex_absences_no_overlap" in str(hata):
            raise HTTPException(
                status_code=409, detail="Bu tarihlerde zaten bir devamsızlık kaydı var."
            ) from hata
        raise HTTPException(status_code=422, detail="Devamsızlık eklenemedi.") from hata
    return await detay(staff_id)


@router.delete("/{staff_id}/absences/{absence_id}", response_model=PersonDetail,
               summary="Devamsızlık sil")
async def izin_sil(staff_id: int, absence_id: int) -> PersonDetail:
    if await repo.izin_sil(staff_id, absence_id) is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return await detay(staff_id)


@router.post("/{staff_id}/availability", response_model=PersonDetail, status_code=201,
             summary="Müsaitlik kuralı ekle")
async def musaitlik_ekle(staff_id: int, istek: AvailabilityCreate) -> PersonDetail:
    await repo.musaitlik_ekle(staff_id, istek.target_date, istek.rule_type, istek.note)
    return await detay(staff_id)


@router.delete("/{staff_id}/availability/{rule_id}", response_model=PersonDetail,
               summary="Müsaitlik kuralı sil")
async def musaitlik_sil(staff_id: int, rule_id: int) -> PersonDetail:
    if await repo.musaitlik_sil(staff_id, rule_id) is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return await detay(staff_id)


@router.post("/{staff_id}/conflicts", response_model=PersonDetail, status_code=201,
             summary="Uyumsuz kişi ekle")
async def uyumsuzluk_ekle(staff_id: int, istek: ConflictCreate) -> PersonDetail:
    if istek.other_staff_id == staff_id:
        raise HTTPException(status_code=422, detail="Kişi kendisiyle uyumsuz olamaz.")
    # Olmayan kişiye referans FK ihlali → ham 500 yerine anlaşılır 404
    if not await repo.personel_var_mi(istek.other_staff_id):
        raise HTTPException(status_code=404, detail="Seçilen personel bulunamadı.")
    await repo.uyumsuzluk_ekle(staff_id, istek.other_staff_id, istek.note)
    return await detay(staff_id)


@router.delete("/{staff_id}/conflicts/{other_id}", response_model=PersonDetail,
               summary="Uyumsuz kişi sil")
async def uyumsuzluk_sil(staff_id: int, other_id: int) -> PersonDetail:
    if not await repo.uyumsuzluk_sil(staff_id, other_id):
        raise HTTPException(status_code=404, detail="Uyumsuzluk kaydı bulunamadı.")
    return await detay(staff_id)


@router.patch("/{staff_id}/contracts/{contract_id}", response_model=PersonDetail,
              summary="Sözleşme düzenle")
async def sozlesme_guncelle(staff_id: int, contract_id: int, istek: ContractUpsert) -> PersonDetail:
    try:
        sonuc = await repo.sozlesme_guncelle(
            staff_id, contract_id, istek.valid_from,
            istek.valid_to + timedelta(days=1) if istek.valid_to else None,
            istek.monthly_target_hours, istek.note,
        )
    except Exception as hata:  # noqa: BLE001
        if "ex_contracts_no_overlap" in str(hata):
            raise HTTPException(status_code=409, detail="Bu tarihlerde zaten bir sözleşme var.") from hata
        raise HTTPException(status_code=422, detail="Sözleşme güncellenemedi.") from hata
    if sonuc is None:
        raise HTTPException(status_code=404, detail="Sözleşme bulunamadı.")
    return await detay(staff_id)


@router.delete("/{staff_id}/contracts/{contract_id}", response_model=PersonDetail,
               summary="Sözleşme sil")
async def sozlesme_sil(staff_id: int, contract_id: int) -> PersonDetail:
    if await repo.sozlesme_sil(staff_id, contract_id) is None:
        raise HTTPException(status_code=404, detail="Sözleşme bulunamadı.")
    return await detay(staff_id)


@router.patch("/{staff_id}/absences/{absence_id}", response_model=PersonDetail,
              summary="Devamsızlık düzenle")
async def izin_guncelle(staff_id: int, absence_id: int, istek: AbsenceCreate) -> PersonDetail:
    if istek.end < istek.start:
        raise HTTPException(status_code=422, detail="Bitiş tarihi başlangıçtan önce olamaz.")
    try:
        sonuc = await repo.izin_guncelle(
            staff_id, absence_id, istek.start, istek.end, istek.absence_type, istek.note
        )
    except Exception as hata:  # noqa: BLE001
        if "ex_absences_no_overlap" in str(hata):
            raise HTTPException(status_code=409, detail="Bu tarihlerde zaten bir kayıt var.") from hata
        raise HTTPException(status_code=422, detail="Devamsızlık güncellenemedi.") from hata
    if sonuc is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return await detay(staff_id)
