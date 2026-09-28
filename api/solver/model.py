"""CP-SAT çözücü — ADIM 5: adalet ve 200 saat.

Adım 2'den devralınan: günde en fazla 1 vardiya, izin/kesin istek günleri boş,
C-017 (sadece gündüzcüler geceye yazılmaz), C-008 (sorumlunun sabit programı),
C-005/C-006 genel mevcut (GEVŞETİLEBİLİR: eksik kalırsa büyük ceza, çizelge yine üretilir).

Adım 3'ün eklediği KATI kurallar — parametreleri veritabanından okunur:
  C-002  en fazla 2 gece arka arkaya
  C-014  2 gece arka arkaya çalışan ertesi gün hiç çalışmaz
  C-021  gece çalışan ertesi gün gündüze yazılmaz          (seeds/014)
  C-016  her Pzt–Paz haftasında en az 1 boş gün
  C-020  oryantasyondaki kişi eşiyle (buddy) aynı gün aynı vardiyada

Geçmiş 7 gün dört zaman kuralının da penceresine girer: dönem öncesi günlerde
değerler sabittir (değiştirilemez), dönem içinde CP-SAT ifadesidir.

Adım 4'ün eklediği GÖREV kuralları — hepsi GEVŞETİLEBİLİR (sağlanamazsa çizelge
yine üretilir, eksik büyük cezayla sayılır ve teşhise kural koduyla yazılır):
  C-011  triyajda en az 3 kişi (TRIYAJ + HASTA_ILT)
  C-010  gözlemde en az 2 kişi; triyaj ve gözlem aynı kişide olamaz
  all_crew_triage_or_observation  sorumlu ve oryantasyon hariç herkes ya triyajda ya gözlemde
  C-009  2 ambulans, ekibin içinden; çıkanlardan sonra triyajda ve gözlemde kalan asgarisi
  C-007  vardiyada en az 1 ekip lideri      (yetkinlik, görev değil)
  count_authority_required  en az 1 sayım yetkilisi  (yetkinlik, görev değil)

Adım 5'in eklediği YUMUŞAK kurallar — ağırlıkları VERİTABANINDAN gelir
(constraints.default_weight), kodda gizli çarpan yoktur:
  C-004  aylık en az 200 saat (izin günü başına düşülerek) — çok yüksek cezalı
  O-002  saat adaleti · O-003 gece · O-004 hafta sonu · O-005 ambulans
  O-001  fazla mesai · C-003 haftalık 50 saat referansı

BİRİM ÖLÇEĞİ burada, veritabanında değil: ağırlıklar "yarım saat başına ceza"
anlamındadır, gece/hafta sonu sayıları vardiya süresiyle çarpılarak yarım saate
çevrilir. Veritabanındaki sayı saf ÖNCELİKTİR.

Bu adımda BİLEREK YOK: C-013 uyumsuz kişi cezası (veri yok).
"""

from __future__ import annotations

import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import psycopg
from ortools.sat.python import cp_model
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.settings import get_settings
from solver import aciklama
from solver.data import SolverVerisi, veriyi_oku
from solver.interface import SolveResult, SolverStatus

# Eksik cezaları artık VERİTABANINDA, kural başına ayrı (seeds/016): genel mevcut
# 2.000.000 > ekip lideri 1.500.000 > triyaj 1.200.000 > ambulans 900.000 >
# gözlem 700.000 > sayım 500.000. Bu sabit yalnız kuralı olmayan bir ihtiyaç
# satırı çıkarsa devreye girer.
EKSIK_CEZASI_YEDEK = 1_000_000

# Atama başına birim maliyet. OLMAZSA fazladan atamanın bedeli sıfırdır, her çözüm
# eşit "optimal" sayılır ve solver keyfî olarak herkesi her güne yazabilir.
# YALNIZ kapsamaya sayılan kişilere uygulanır: maliyetin amacı EKİBİ şişirmemek,
# oryantasyondaki kişi ise ekip mevcuduna sayılmıyor.
ATAMA_MALIYETI = 1



# Ambulans rozeti başına birim maliyet. Adım 2'deki tuzağın aynısı: maliyet olmazsa
# fazladan rozetin bedeli sıfır olur ve solver keyfî olarak herkese ambulans yazabilir.
ROZET_MALIYETI = 1

# C-004 (aylık 200 saat) katı bir kuraldır, ağırlığı yok — gevşetildiğinde
# kullanılacak ceza burada. Kapsama eksiğinin 1/2000'i: bir vardiyayı boş
# bırakmaktansa birini 25 saat eksik çalıştırmayı tercih eder.
SAAT_EKSIGI_CEZASI = 20_000

# Demo tekrarlanabilir olsun diye sabit tohum.
# Adalet cezasının iki parçasından uç farkı (max−min) açık mı.
# Ölçüm (30 sn, Ekim 2026): açıkken amaç ~583.000, kapalıyken ~524.000 — ama
# kapalıyken uçlar denetimsiz kalıyor. Açık bırakıyoruz; kapatmak modeli
# hafifletmek istendiğinde ilk başvurulacak düğme.
UC_FARKI_CEZALANDIR = True
RASTGELE_TOHUM = 20261001

# Sayısı TAM olması gereken görevler. Ambulans fiziksel bir araçtır: ihtiyaç
# satırı "en az 2" der ama 3 kişi göndermek hata olur. Diğer slotlarda fazlası
# zararsızdır (C-005: "fazlası sorun değil"), o yüzden liste dar tutuluyor.
TAM_SAYILI_GOREVLER = frozenset({"AMBULANS"})

# C-008'in Cumartesi yarısı. Kural "Cumartesi 08:30–14:00" diyor, GUNDUZ_CMT (5,5 sa)
# tam bunun için var. Kağıda dönmek istenirse tek değişiklik: "GUNDUZ".
SORUMLU_CUMARTESI = "GUNDUZ_CMT"
SORUMLU_ROL = "sorumlu_hemsire"

# C-016 bir haftanın kaç gününü bilirsek kuralı uygularız. Dönemin ucundaki yarım
# haftada bilinen gün sayısı azaldıkça kural anlamını yitirir: bir haftanın yalnız
# 1 günü dönem içindeyse "o haftada 1 boş gün olsun" o TEK günü boşaltmak demektir
# ve kimse çalışamaz (30 Kasım 2026 Pazartesi tam böyleydi). Kişi dinlenme gününü
# haftanın bilmediğimiz kısmında kullanabilir. Haftanın çoğunluğunu (4 gün)
# biliyorsak kuralı uyguluyoruz.
C016_ASGARI_BILINEN_GUN = 4

# Geçmişe bakış penceresi (gün). En uzun geri bakış C-016'nın haftasıdır.
GECMIS_GUN = 7


def run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult:
    baslangic = time.monotonic()
    settings = get_settings()
    veri = veriyi_oku(draft_id)

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # Koşu kaydı HEMEN commit edilir: hata yolundaki rollback bu satırı da
            # geri alırsa teşhis yazılacak run_id kalmaz.
            run_id = _kosuyu_bul_veya_ac(cur, draft_id, time_limit_s)
            conn.commit()
            try:
                cozum = _coz(veri, time_limit_s)
                atama_sayisi = _atamalari_yaz(cur, draft_id, veri, cozum)
                teshis_sayisi = _teshisleri_yaz(cur, run_id, veri, cozum)
                cur.execute(
                    """
                    UPDATE solver_runs
                       SET status = %s, finished_at = CURRENT_TIMESTAMP,
                           objective_value = %s, params_snapshot = %s
                     WHERE id = %s
                    """,
                    (cozum.durum, cozum.amac, Json(_parametre_fotografi(veri, cozum)), run_id),
                )
                conn.commit()
                # Kontrolcü ancak COMMIT'ten SONRA koşabilir: kendi bağlantısını
                # açıyor ve yazılmamış satırları göremez.
                teshis_sayisi += _kontrolcuyu_calistir(cur, run_id, draft_id, veri)
                conn.commit()
            except Exception as hata:  # noqa: BLE001 — koşu kaydı her hâlükârda kapanmalı
                conn.rollback()
                cur.execute(
                    "UPDATE solver_runs SET status='HATA', finished_at=CURRENT_TIMESTAMP WHERE id=%s",
                    (run_id,),
                )
                cur.execute(
                    """INSERT INTO solver_diagnostics (solver_run_id, severity, message)
                       VALUES (%s, 'uyari', %s)""",
                    (run_id, f"Çözücü hata verdi: {hata}"),
                )
                conn.commit()
                return SolveResult(
                    run_id=run_id, status="HATA", objective_value=None,
                    assignment_count=0, diagnostic_count=1,
                    elapsed_s=time.monotonic() - baslangic,
                )

    return SolveResult(
        run_id=run_id, status=cozum.durum, objective_value=cozum.amac,
        assignment_count=atama_sayisi, diagnostic_count=teshis_sayisi,
        elapsed_s=time.monotonic() - baslangic,
    )


@dataclass(frozen=True)
class Eksik:
    """Gevşetilen bir kuralın o gün o vardiyadaki açığı."""

    gun: date
    vardiya_kodu: str
    slot: str                 # GENEL | TRIYAJ | GOZLEM | AMBULANS | SAYIM | ROZETSIZ | KALAN_*
    kural_kodu: str | None    # constraints.code
    adet: int
    gereken: int


class _IyilesmeIzleyici(cp_model.CpSolverSolutionCallback):
    """Her yeni çözümde saati sıfırlar. Durdurma kararını gözcü iş parçacığı verir."""

    def __init__(self) -> None:
        super().__init__()
        self.son_iyilesme = time.monotonic()
        self.cozum_sayisi = 0

    def on_solution_callback(self) -> None:
        self.son_iyilesme = time.monotonic()
        self.cozum_sayisi += 1


def _durgunlukta_durdur(solver: cp_model.CpSolver, izleyici: _IyilesmeIzleyici,
                        esik_s: int, bitti: threading.Event) -> dict:
    """X saniye daha iyi çözüm gelmezse aramayı durdurur.

    NEDEN AYRI İŞ PARÇACIĞI: çözüm geri çağırması yalnız YENİ bir çözüm bulununca
    çalışır. Solver 5. saniyede iyi bir çözüm bulup sonra hiç iyileşme bulamazsa
    geri çağırma bir daha hiç tetiklenmez — yani durdurma kararını orada veremeyiz.
    Bu iş parçacığı yarım saniyede bir saate bakar ve gerekirse stop_search()
    çağırır; CP-SAT'ın kendi max_time_in_seconds'ı üst sınır olarak kalır.
    """
    durum = {"durdurdu": False, "durgunluk_s": 0.0}
    if not esik_s:
        return durum

    def gozcu() -> None:
        while not bitti.wait(0.5):
            durgun = time.monotonic() - izleyici.son_iyilesme
            if durgun >= esik_s:
                durum["durdurdu"] = True
                durum["durgunluk_s"] = round(durgun, 1)
                solver.stop_search()
                return

    iplik = threading.Thread(target=gozcu, name="solver-durgunluk", daemon=True)
    iplik.start()
    durum["iplik"] = iplik
    return durum


class Cozum:
    def __init__(self) -> None:
        self.durum: SolverStatus = "HATA"
        self.amac: Decimal | None = None
        self.atamalar: list[tuple[int, date, str]] = []
        self.rozetler: list[tuple[int, date, str, str]] = []   # kişi, gün, vardiya, görev
        self.takviyeler: list[tuple[int, date, str]] = []      # C-022 acil takviye
        self.eksikler: list[Eksik] = []
        self.cozum_suresi: float = 0.0
        self.degisken_sayisi: int = 0
        self.gorev_degiskeni: int = 0
        self.saat_eksikleri: dict[int, int] = {}      # personel_id → eksik yarım saat
        self.karsilanmayan_istekler: list[tuple[int, date, str]] = []
        self.hedefler: dict[str, int] = {}            # adalet hedefleri (rapor için)
        self.kisit_sayisi: int = 0
        self.erken_durdu: bool = False
        self.durgunluk_s: float = 0.0


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


def _coz(v: SolverVerisi, time_limit_s: int) -> Cozum:
    model = cp_model.CpModel()
    sonuc = Cozum()

    yok = {(y.personel_id, y.gun) for y in v.yokluklar}
    bos = {(i.personel_id, i.gun) for i in v.kesin_istekler if i.tur == "BOS_GUN"}
    yalniz_gunduz = {(i.personel_id, i.gun) for i in v.kesin_istekler if i.tur == "SADECE_GUNDUZ"}
    yalniz_gece = {(i.personel_id, i.gun) for i in v.kesin_istekler if i.tur == "SADECE_GECE"}
    # Sadece gündüz çalışan biri için O GÜNE ÖZEL gece değişkeni: SADECE_GECE
    # isteği varsa (gücü ne olursa olsun) o gün gece seçeneği açılır.
    #   KESIN    → gündüz değişkenleri de kapandığı için gece ZORUNLU olur
    #   MUMKUNSE → gündüz de açık kalır, karşılanmazsa O-006 cezası yazılır
    # Kişinin genel çalışma tipi (sadece_gunduz) DEĞİŞMEZ; istisna tek güne aittir.
    gece_istisnasi = {
        (i.personel_id, i.gun)
        for i in v.kesin_istekler + v.tercih_istekler
        if i.tur == "SADECE_GECE"
    }
    sabit_gun = {(s.personel_id, s.gun) for s in v.sabit_atamalar}
    engelli = yok | bos | sabit_gun

    # Sorumlunun programı sabit (C-008) → değişkeni yok. Oryantasyondakiler ARTIK
    # atanıyor (C-020 onları eşine bağlıyor), ama kapsamaya sayılmıyorlar.
    atanabilirler = [p for p in v.personel if p.rol_kodu != SORUMLU_ROL]
    kapsama_sayilan = {p.id for p in v.personel if p.kapsamaya_sayilir}

    # ----- Değişkenler -----
    # İmkânsız üçlü için değişken AÇILMIYOR: model küçülür ve "değişken yok"
    # ihlal edilmesi imkânsız bir kuraldır.
    x: dict[tuple[int, date, str], cp_model.IntVar] = {}
    for p in atanabilirler:
        for g in v.gunler:
            if (p.id, g) in engelli:
                continue
            for s in v.vardiyalar:
                if not s.secenek_mi(p.rol_kodu, g.isoweekday()):
                    continue                                  # GUNDUZ_CMT yalnız sorumlu+Cmt
                if s.gece_mi and (p.id, g) in yalniz_gunduz:
                    continue                                  # KESIN "sadece gündüz" isteği
                if (s.gece_mi and p.uygunluk == "sadece_gunduz"
                        and (p.id, g) not in gece_istisnasi):
                    continue                                  # C-017, istisnası yoksa
                if not s.gece_mi and (p.uygunluk == "sadece_gece" or (p.id, g) in yalniz_gece):
                    continue
                x[p.id, g, s.kod] = model.new_bool_var(f"x_{p.id}_{g}_{s.kod}")
    sonuc.degisken_sayisi = len(x)

    sorumlu_plani = _sorumlu_plani(v, engelli)

    # ----- Zaman çizgisi: geçmiş + dönem -----
    gece, gunduz, calisiyor, tum_gunler = _zaman_cizgisi(v, x, sorumlu_plani)
    donem = set(v.gunler)

    # ----- Kısıt 1: günde en fazla 1 vardiya -----
    gunun_vardiyalari: dict[tuple[int, date], list] = defaultdict(list)
    for (p_id, g, _kod), degisken in x.items():
        gunun_vardiyalari[p_id, g].append(degisken)
    for degiskenler in gunun_vardiyalari.values():
        if len(degiskenler) > 1:
            model.add_at_most_one(degiskenler)

    # ----- C-022: acil takviye değişkenleri (kapsama kısıtından ÖNCE) -----
    takviye = _acil_takviye_degiskenleri(model, v, x)

    # ----- Kısıt 2: genel mevcut (gevşetilebilir) -----
    # Gereken sayı koda YAZILMAZ, ihtiyaç şablonunun GENEL satırlarından gelir.
    sabit_kapsama = _sabit_kapsama_sayimi(v)
    # Gevşeme değişkenleri tek sözlükte: anahtar (gün, vardiya, slot) → (değişken, satır)
    # Gevşeme değişkenleri tek yerde: (gün, vardiya, slot) → (değişken, kural kodu, gereken)
    eksik: dict[tuple[date, str, str], tuple[cp_model.IntVar, str | None, int]] = {}

    def gevset(g: date, vardiya_kodu: str, slot: str, gereken: int,
               kural_kodu: str | None) -> cp_model.IntVar:
        e = model.new_int_var(0, gereken, f"eksik_{slot}_{g}_{vardiya_kodu}")
        eksik[g, vardiya_kodu, slot] = (e, kural_kodu, gereken)
        return e

    gunun_atamalari: dict[tuple[date, str], list] = defaultdict(list)
    for (p_id, gun, kod), d in x.items():
        if p_id in kapsama_sayilan:
            gunun_atamalari[gun, kod].append(d)

    for satir in v.ihtiyaclar:
        if satir.slot_kodu != "GENEL":
            continue
        for g in satir.gunler:
            e = gevset(g, satir.vardiya_kodu, "GENEL", satir.min_sayi, satir.kural_kodu)
            # Acil takviye (C-022) genel mevcuda SAYILIR — tek amacı bu.
            takviyeler = [d for (_p, gun, kod), d in takviye.items()
                          if gun == g and kod == satir.vardiya_kodu]
            ekip = (sum(gunun_atamalari.get((g, satir.vardiya_kodu), []))
                    + sabit_kapsama.get((g, satir.vardiya_kodu), 0))
            model.add(ekip + sum(takviyeler) + e >= satir.min_sayi)
            if takviyeler:
                # C-022 KATI SINIR: takviye yalnız AÇIĞI kapatacak kadar
                # kullanılabilir; 5/5 dolu bir vardiyaya oryantasyondaki hiçbir
                # koşulda eklenemez.
                #
                # Sınır YALNIZ takviye kullanıldığında devreye girer. Koşulsuz
                # yazılsaydı (ekip + takviye <= gereken) normal ekibi de gerekene
                # kilitlerdi: "fazlası sorun değil" (C-005) serbestliği kalkar ve
                # ölçtük — Ekim'de saat farkı 3,0'dan 9,5'e çıkıyor. Oysa kural
                # ekibin fazlasını değil, oryantasyonun fazlasını yasaklıyor.
                tak_var = model.new_bool_var(f"takviye_var_{g}_{satir.vardiya_kodu}")
                model.add(sum(takviyeler) == 0).only_enforce_if(tak_var.Not())
                model.add(ekip + sum(takviyeler) <= satir.min_sayi).only_enforce_if(tak_var)

    # ----- Kısıt 3–6: zaman kuralları (geçmiş dahil) -----
    kisiler = atanabilirler + [p for p in v.personel if p.rol_kodu == SORUMLU_ROL]
    _ardisik_gece(model, v, kisiler, gece, tum_gunler, donem)              # C-002
    _iki_gece_sonrasi_bos(model, v, kisiler, gece, calisiyor, tum_gunler, donem)  # C-014
    _gece_sonrasi_gunduz_yok(model, kisiler, gece, gunduz, tum_gunler, donem)     # C-021
    _haftalik_bos_gun(model, v, kisiler, calisiyor, tum_gunler, donem)     # C-016
    _oryantasyon_esi(model, v, x, takviye, engelli)                       # C-020

    # ----- Görevler (Adım 4) -----
    t = _gorev_degiskenleri(model, v, x, kapsama_sayilan)
    sonuc.gorev_degiskeni = len(t)
    _gorev_kisitlari(model, v, x, t, kapsama_sayilan, gevset, takviye)
    _yetkinlik_slotlari(model, v, x, sorumlu_plani, gevset)

    # ----- Amaç -----
    # Atama maliyeti yalnız kapsamaya SAYILAN kişilere: maliyetin amacı ekibi
    # şişirmemek. Oryantasyondakilere uygulanırsa eğitim hemşiresini kullanmak
    # 3 birim eder ve solver onu kullanmaktan kaçınır — kural ters teper.
    ekip_atamalari = [d for (p_id, _g, _k), d in x.items() if p_id in kapsama_sayilan]
    ambulans_rozetleri = [d for (_p, _g, _v, gorev), d in t.items() if gorev == "AMBULANS"]
    # Her eksik KENDİ kuralının ağırlığıyla cezalanır (seeds/016 kademeleri).
    temel: list[tuple[int, object]] = [
        (ATAMA_MALIYETI, sum(ekip_atamalari)),
        (ROZET_MALIYETI, sum(ambulans_rozetleri)),
    ]
    for (_g, _vd, _slot), (e, kural_kodu, _n) in eksik.items():
        kural = v.kurallar.get(kural_kodu) if kural_kodu else None
        temel.append((int(kural.agirlik) if kural and kural.agirlik else EKSIK_CEZASI_YEDEK, e))
    takviye_kural = v.kural("C-022")
    if takviye and takviye_kural and takviye_kural.agirlik:
        temel.append((int(takviye_kural.agirlik), sum(takviye.values())))

    adalet_terimleri, olcumler = _adalet_ve_saat(model, v, x, t, kapsama_sayilan)
    adalet_terimleri += _tercihler(model, v, x, t, kapsama_sayilan, olcumler)
    sonuc.hedefler = olcumler["hedefler"]

    solver = cp_model.CpSolver()
    solver.parameters.num_workers = get_settings().solver_workers
    solver.parameters.random_seed = RASTGELE_TOHUM

    model.minimize(sum(agirlik * ifade for agirlik, ifade in temel + adalet_terimleri))
    solver.parameters.max_time_in_seconds = float(time_limit_s)      # üst sınır
    _baslangic_ipucu(model, v, x, t)

    izleyici = _IyilesmeIzleyici()
    bitti = threading.Event()
    gozcu = _durgunlukta_durdur(solver, izleyici, get_settings().solver_no_improvement_s, bitti)
    try:
        durum = solver.solve(model, izleyici)
    finally:
        bitti.set()
        if (iplik := gozcu.get("iplik")) is not None:
            iplik.join(timeout=2)
    sonuc.erken_durdu = gozcu["durdurdu"]
    sonuc.durgunluk_s = gozcu["durgunluk_s"]

    sonuc.durum = _durumu_cevir(durum)
    sonuc.cozum_suresi = solver.wall_time
    sonuc.kisit_sayisi = len(model.proto.constraints)
    if durum in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sonuc.amac = Decimal(str(solver.objective_value))
        sonuc.atamalar = [anahtar for anahtar, d in x.items() if solver.value(d)]
        sonuc.atamalar += list(sorumlu_plani)
        sonuc.rozetler = [anahtar for anahtar, d in t.items() if solver.value(d)]
        sonuc.takviyeler = [anahtar for anahtar, d in takviye.items() if solver.value(d)]
        sonuc.saat_eksikleri = {
            p_id: solver.value(e) for p_id, e in olcumler["eksik_saat"].items()
            if solver.value(e) > 0
        }
        sonuc.karsilanmayan_istekler = [
            anahtar for anahtar, b in olcumler.get("karsilanmayan_istekler", {}).items()
            if solver.value(b)
        ]
        for (g, vardiya_kodu, slot), (e, kural_kodu, gereken) in eksik.items():
            if (adet := solver.value(e)) > 0:
                sonuc.eksikler.append(Eksik(g, vardiya_kodu, slot, kural_kodu, adet, gereken))
    return sonuc


def _baslangic_ipucu(model, v: SolverVerisi, x: dict, t: dict) -> None:
    """Taslakta duran atamaları CP-SAT'a başlangıç ipucu olarak verir.

    Kısıt değil ipucu: solver istediği gibi değiştirebilir, ipucu kurallara
    uymuyorsa onarır. Amacı "kopyala → çöz" akışında aramanın kaynak çizelgenin
    yakınından başlaması — böylece sonuç kaynaktan kötüye gitmiyor.

    Adım 5'te denenen ve işe yaramayan iki fazlı ipucudan farkı: orada ipucu
    solver'ın KENDİ ilk fazından geliyordu ve aramayı kendi bulduğu yere
    kilitliyordu. Buradaki ipucu dışarıdan, insan eliyle ya da önceki bir
    koşudan gelen gerçek bir çizelge.
    """
    verilen = 0
    for a in v.mevcut_atamalar:
        degisken = x.get((a.personel_id, a.gun, a.vardiya_kodu))
        if degisken is None:
            continue
        model.add_hint(degisken, 1)
        verilen += 1
        for gorev in a.gorevler:
            rozet = t.get((a.personel_id, a.gun, a.vardiya_kodu, gorev))
            if rozet is not None:
                model.add_hint(rozet, 1)
    return verilen


def _zaman_cizgisi(v: SolverVerisi, x: dict, sorumlu_plani: list[tuple[int, date, str]]):
    """Kişi-gün başına 'gece', 'gündüz', 'çalışıyor' ifadeleri.

    Dönem günlerinde CP-SAT değişkenlerinin toplamı; geçmiş günlerde ve sabit
    satırlarda düz sayı (0/1). Aynı kısıt yazımı iki tarafta da çalışsın diye:
    sınırda ayrı kod yok, ifade ile sabit yan yana toplanabiliyor.
    """
    gece_kodlari = {s.kod for s in v.vardiyalar if s.gece_mi}
    gece_p: dict[tuple[int, date], list] = defaultdict(list)
    gunduz_p: dict[tuple[int, date], list] = defaultdict(list)

    def ekle(p_id: int, g: date, kod: str, deger) -> None:
        (gece_p if kod in gece_kodlari else gunduz_p)[p_id, g].append(deger)

    for (p_id, g, kod), degisken in x.items():
        ekle(p_id, g, kod, degisken)
    for p_id, g, kod in sorumlu_plani:
        ekle(p_id, g, kod, 1)
    for s in v.sabit_atamalar:
        ekle(s.personel_id, s.gun, s.vardiya_kodu, 1)
    for a in v.gecmis:                                   # değiştirilemez geçmiş
        ekle(a.personel_id, a.gun, a.vardiya_kodu, 1)

    gece = lambda p_id, g: sum(gece_p.get((p_id, g), []))        # noqa: E731
    gunduz = lambda p_id, g: sum(gunduz_p.get((p_id, g), []))    # noqa: E731
    calisiyor = lambda p_id, g: gece(p_id, g) + gunduz(p_id, g)  # noqa: E731

    ilk = v.donem_bas - timedelta(days=GECMIS_GUN)
    tum_gunler = [ilk + timedelta(days=i) for i in range((v.gunler[-1] - ilk).days + 1)]
    return gece, gunduz, calisiyor, tum_gunler


def _ardisik_gece(model, v: SolverVerisi, kisiler, gece, tum_gunler, donem) -> None:
    """C-002: n+1 günlük her pencerede en fazla n gece."""
    n = int(v.kural("C-002").parametreler["max_consecutive_nights"])
    for p in kisiler:
        for i in range(len(tum_gunler) - n):
            pencere = tum_gunler[i:i + n + 1]
            # Tamamı geçmişte kalan pencere DEĞİŞTİRİLEMEZ; kısıt yazmak modeli
            # geçmişteki bir ihlal yüzünden çözümsüz yapardı.
            if not any(g in donem for g in pencere):
                continue
            model.add(sum(gece(p.id, g) for g in pencere) <= n)


def _iki_gece_sonrasi_bos(model, v: SolverVerisi, kisiler, gece, calisiyor, tum_gunler, donem) -> None:
    """C-014: n gece arka arkaya çalışıldıysa ertesi gün hiç çalışılmaz.

    'n gece + o gün çalışma ≤ n' okunuşu: geceler doluysa toplam zaten n'dir,
    o hâlde ertesi günün çalışma göstergesi 0 olmak zorunda.
    rest_gap_hours=24 ile birebir: ikinci gece d+2'de 08:30'da biter, 24 saat
    sonrası d+3'ün 08:30'u — yani d+2 tamamen boş, d+3 gündüzü serbest.
    """
    n = int(v.kural("C-014").parametreler["rest_trigger_nights"])
    for p in kisiler:
        for i in range(len(tum_gunler) - n):
            geceler = tum_gunler[i:i + n]
            ertesi = tum_gunler[i + n]
            if ertesi not in donem:          # sonuç günü dönem dışındaysa yapacak bir şey yok
                continue
            model.add(sum(gece(p.id, g) for g in geceler) + calisiyor(p.id, ertesi) <= n)


def _gece_sonrasi_gunduz_yok(model, kisiler, gece, gunduz, tum_gunler, donem) -> None:
    """C-021: gece 08:30'da biter, gündüz 08:30'da başlar — ikisi arka arkaya olamaz."""
    for p in kisiler:
        for i in range(len(tum_gunler) - 1):
            g, ertesi = tum_gunler[i], tum_gunler[i + 1]
            if ertesi not in donem:
                continue
            model.add(gece(p.id, g) + gunduz(p.id, ertesi) <= 1)


def _haftalik_bos_gun(model, v: SolverVerisi, kisiler, calisiyor, tum_gunler, donem) -> None:
    """C-016: her Pzt–Paz haftasında en az 1 boş gün (o gün başlayan vardiya yok).

    BİLİNEN gün = dönem içi ya da geçmiş penceresinde. Bunun dışındaki günler
    (örn. 1 Kasım) hesaba girmez. Ay başındaki yarım hafta geçmiş günlerle
    tamamlanır; dönem sonundaki yarım haftada kural bilinen günlere uygulanır.

    MUAFİYET: sabit programlı kişi (sorumlu hemşire) dönem sonundaki yarım
    haftada muaftır — dinlenme günü (Pazar) dönemin dışına düşüyor, kuralı
    pencereye sıkıştırmak sabit programı yapay olarak bozardı.
    """
    en_az = int(v.kural("C-016").parametreler["weekly_min_rest_events"])
    bilinen_gunler = set(tum_gunler)
    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        if pzt not in haftalar:
            haftalar[pzt] = [
                pzt + timedelta(days=i) for i in range(7)
                if (pzt + timedelta(days=i)) in bilinen_gunler
            ]

    for pzt, gunler in haftalar.items():
        if len(gunler) < C016_ASGARI_BILINEN_GUN:
            continue
        tam_hafta = len(gunler) == 7
        for p in kisiler:
            if not tam_hafta and p.rol_kodu == SORUMLU_ROL:
                continue                                   # muafiyet
            model.add(sum(calisiyor(p.id, g) for g in gunler) <= len(gunler) - en_az)


def _oryantasyon_esi(model, v: SolverVerisi, x: dict, takviye: dict, engelli: set) -> None:
    """C-020: oryantasyondaki kişi eşiyle aynı gün aynı vardiyada.

    EŞİTLİK: eğitim hemşiresi hangi vardiyada çalışıyorsa oryantasyondaki de
    yanındadır. Yalnız '≤' yazsaydık kural "eşi yoksa çalışamaz" derdi ama
    çalışmasını GEREKTİRMEZDİ; oryantasyondaki kapsamaya sayılmadığı için
    solver onu hiç atamazdı.

    İSTİSNA: oryantasyondaki kişi o gün izinli/raporlu ya da KESIN bir
    BOS_GUN isteği varsa eşitlik aranmaz — yoksa eğitim hemşiresi de o gün
    çalışamaz hale gelirdi.

    Eşin alabildiği ama oryantasyondakinin alamadığı bir vardiya varsa (örn.
    eş gece çalışabiliyor, oryantasyondaki yalnız gündüz) eşe kısıt konmaz:
    eğitim hemşiresinin başka görevleri olabilir.

    ACİL TAKVİYE (C-022): eşitlik takviye değişkeniyle gevşer.
        x[oryantasyon] >= x[eş]              eş çalışıyorsa yanındadır (gölgeleme)
        x[oryantasyon] <= x[eş] + takviye    eşsiz çalışması YALNIZ takviyeyle olur
    İkisi birlikte, takviye 0 iken eski eşitliğin aynısıdır.
    """
    for o in v.personel:
        if not o.oryantasyonda or o.buddy_id is None:
            continue
        for g in v.gunler:
            if (o.id, g) in engelli:
                continue
            for s in v.vardiyalar:
                oryantasyon = x.get((o.id, g, s.kod))
                if oryantasyon is None:
                    continue
                tak = takviye.get((o.id, g, s.kod))
                es = x.get((o.buddy_id, g, s.kod))
                if es is None:
                    # Eş o vardiyayı hiç alamıyor: yalnız acil takviyeyle çalışabilir.
                    model.add(oryantasyon <= (tak if tak is not None else 0))
                elif tak is None:
                    model.add(oryantasyon == es)
                else:
                    model.add(oryantasyon >= es)
                    model.add(oryantasyon <= es + tak)


def _adalet_ve_saat(model, v: SolverVerisi, x: dict, t: dict,
                    kapsama_sayilan: set[int]) -> tuple[list[tuple[int, object]], dict]:
    """C-004, O-001…O-005 ve C-003.

    Ağırlıklar VERİTABANINDAN (constraints.default_weight), kodda gizli çarpan yok.
    BİRİM ÖLÇEĞİ burada: ağırlık "yarım saat başına ceza" demektir, gece ve hafta
    sonu sayıları adet cinsinden olduğu için vardiya süresiyle çarpılıp yarım saate
    çevrilir (bir gece 29 yb, ortalama vardiya 24 yb). Ambulans rozeti bir GÖREVdir,
    süre değil — ölçeklenmez.

    Döndürür: (amaç terimleri, çözümden sonra okunacak değişkenler)
    """
    terimler: list[tuple[int, object]] = []
    kisiler = [p for p in v.personel if p.id in kapsama_sayilan]
    sure = {vd.kod: vd.sure_yb for vd in v.vardiyalar}
    gece_kodlari = {vd.kod for vd in v.vardiyalar if vd.gece_mi}
    gece_yb = max((vd.sure_yb for vd in v.vardiyalar if vd.gece_mi), default=29)
    vardiya_yb = round(sum(sure.values()) / len(sure))

    def agirlik(katalog: str) -> int:
        kural = v.kural(katalog)
        return int(kural.agirlik) if kural and kural.agirlik else 0

    # ---- Kişi başına toplamlar ----
    kisi_gunleri: dict[int, list] = defaultdict(list)
    for (p_id, g, kod), d in x.items():
        kisi_gunleri[p_id].append((g, kod, d))

    saat, gece, hafta_sonu, ambulans = {}, {}, {}, {}
    for p in kisiler:
        kendi = kisi_gunleri[p.id]
        saat[p.id] = sum(d * sure[kod] for _g, kod, d in kendi)
        gece[p.id] = sum(d for _g, kod, d in kendi if kod in gece_kodlari)
        hafta_sonu[p.id] = sum(d for g, _k, d in kendi if g.isoweekday() >= 6)
    for p in kisiler:
        ambulans[p.id] = sum(
            d for (p_id, _g, _v, gorev), d in t.items()
            if p_id == p.id and gorev == "AMBULANS"
        )

    # ---- C-004: aylık en az 200 saat (izin günü başına düşülerek) ----
    izin = Counter(y.personel_id for y in v.yokluklar)
    dusum = v.kural("C-004").parametreler.get("absence_daily_reduction_hours")
    dusum_yb = int(Decimal(dusum) * 2) if dusum is not None else 0

    hedef_saat, eksik_saat = {}, {}
    for p in kisiler:
        hedef = max(0, p.hedef_saat_yb - izin[p.id] * dusum_yb)
        hedef_saat[p.id] = hedef
        e = model.new_int_var(0, hedef, f"saat_eksik_{p.id}")
        model.add(saat[p.id] + v.ay_basi_saatler_yb.get(p.id, 0) + e >= hedef)
        eksik_saat[p.id] = e
    terimler.append((SAAT_EKSIGI_CEZASI, sum(eksik_saat.values())))

    # ---- O-001: 200 saat üstü fazla mesai ----
    fazlalar = []
    for p in kisiler:
        f = model.new_int_var(0, 2000, f"fazla_{p.id}")
        model.add(f >= saat[p.id] - hedef_saat[p.id])
        fazlalar.append(f)
    terimler.append((agirlik("O-001"), sum(fazlalar)))

    # ---- O-002…O-005: adalet ----
    # Her biri İKİ parça: uçlar arası fark + herkesin hedefe uzaklığı. Sadece
    # max−min cezalandırmak ortadaki kişileri görmez — iki uç düzelir, geri kalan
    # çarpık kalır.
    gece_havuzu = [p for p in kisiler if p.uygunluk != "sadece_gunduz"]
    amb_havuzu = [p for p in kisiler if "AMBULANS" in p.yetkinlikler]
    beklenen = _beklenen_yukler(v)
    hedefler: dict[str, int] = {}

    for katalog, ad, deger, havuz, olcek, ust in (
        ("O-002", "saat",       saat,       kisiler,     1,          1200),
        ("O-003", "gece",       gece,       gece_havuzu, gece_yb,      40),
        ("O-004", "hafta_sonu", hafta_sonu, kisiler,     vardiya_yb,   40),
        ("O-005", "ambulans",   ambulans,   amb_havuzu,  1,            80),
    ):
        w = agirlik(katalog)
        if not w or len(havuz) < 2:
            continue
        hedef_ort = round(beklenen[ad] / len(havuz))
        hedefler[ad] = hedef_ort
        degerler = [deger[p.id] for p in havuz]

        if UC_FARKI_CEZALANDIR:
            en_cok = model.new_int_var(0, ust, f"encok_{ad}")
            en_az = model.new_int_var(0, ust, f"enaz_{ad}")
            model.add_max_equality(en_cok, degerler)
            model.add_min_equality(en_az, degerler)
            terimler.append((w * olcek, en_cok - en_az))

        sapmalar = []
        for p in havuz:
            sp = model.new_int_var(0, ust, f"sapma_{ad}_{p.id}")
            model.add(sp >= deger[p.id] - hedef_ort)
            model.add(sp >= hedef_ort - deger[p.id])
            sapmalar.append(sp)
        terimler.append((w * olcek, sum(sapmalar)))

    # ---- C-003: haftalık 50 saat referansı ----
    # YALNIZ dönemin içinde kalan TAM haftalar. Ay başı/sonu yarım haftasında
    # 50 saat zaten imkânsız; uygulamak kaçınılmaz bir ceza üretirdi.
    haftalik = v.kural("C-003")
    if haftalik and haftalik.agirlik:
        referans_yb = int(Decimal(haftalik.parametreler["weekly_reference_hours"]) * 2)
        donem = set(v.gunler)
        haftalar: dict[date, list[date]] = {}
        for g in v.gunler:
            pzt = g - timedelta(days=g.weekday())
            haftalar.setdefault(pzt, [pzt + timedelta(days=i) for i in range(7)])
        tam_haftalar = [gunler for gunler in haftalar.values() if set(gunler) <= donem]
        sapmalar = []
        for p in kisiler:
            gunluk = {g: (kod, d) for g, kod, d in kisi_gunleri[p.id]}
            for gunler in tam_haftalar:
                hafta_yb = sum(
                    d * sure[kod] for g in gunler if g in gunluk
                    for kod, d in [gunluk[g]]
                )
                sp = model.new_int_var(0, 400, f"hafta_{p.id}_{gunler[0]}")
                model.add(sp >= hafta_yb - referans_yb)
                model.add(sp >= referans_yb - hafta_yb)
                sapmalar.append(sp)
        if sapmalar:
            terimler.append((int(haftalik.agirlik), sum(sapmalar)))

    olcumler = {"hedefler": hedefler, "hedef_saat": hedef_saat, "eksik_saat": eksik_saat,
                "tam_hafta_sayisi": len(tam_haftalar) if haftalik else 0}
    return terimler, olcumler


def _tercihler(model, v: SolverVerisi, x: dict, t: dict,
               kapsama_sayilan: set[int], olcumler: dict) -> list[tuple[int, object]]:
    """O-006 karşılanamayan istek · O-007 triyajda hasta iletişimi · O-008 ambulans alan dağılımı.

    Üçü de YUMUŞAK: ihlal çizelgeyi engellemez, ceza puanı yazar. Ağırlıklar
    veritabanından (seeds/016).
    """
    terimler: list[tuple[int, object]] = []
    gece_kodlari = {vd.kod for vd in v.vardiyalar if vd.gece_mi}

    # ---- O-006: karşılanamayan 'mümkünse' tercihi ----
    # KESIN istekler değişken açılırken zaten elendi (katı). MUMKUNSE olanlar
    # buraya kadar hiç kullanılmıyordu — Adım 1'de söz verilen ceza burada.
    kural = v.kural("O-006")
    karsilanmayanlar: dict[tuple[int, date, str], object] = {}
    if kural and kural.agirlik:
        for istek in v.tercih_istekler:
            gunun = [(kod, d) for (p_id, g, kod), d in x.items()
                     if p_id == istek.personel_id and g == istek.gun]
            if not gunun:
                continue
            if istek.tur == "BOS_GUN":
                ihlal = sum(d for _kod, d in gunun)                 # o gün çalışıyorsa
            elif istek.tur == "SADECE_GUNDUZ":
                ihlal = sum(d for kod, d in gunun if kod in gece_kodlari)
            elif istek.tur == "SADECE_GECE":
                ihlal = sum(d for kod, d in gunun if kod not in gece_kodlari)
            else:
                continue
            b = model.new_bool_var(f"istek_{istek.personel_id}_{istek.gun}")
            model.add(b >= ihlal)
            karsilanmayanlar[istek.personel_id, istek.gun, istek.tur] = b
            terimler.append((int(kural.agirlik), b))
    olcumler["karsilanmayan_istekler"] = karsilanmayanlar

    # ---- O-007: triyaja mümkünse hasta iletişimi olanlar ----
    # HASTA_ILT artık ihtiyaç satırında ŞART değil (seeds/016), TERCİH.
    kural = v.kural("O-007")
    if kural and kural.agirlik:
        yetkinlik = {p.id: p.yetkinlikler for p in v.personel}
        iletisimsiz = [
            d for (p_id, _g, _vd, gorev), d in t.items()
            if gorev == "TRIYAJ" and "HASTA_ILT" not in yetkinlik[p_id]
        ]
        if iletisimsiz:
            terimler.append((int(kural.agirlik), sum(iletisimsiz)))

    # ---- O-008: ambulans ekibi mümkünse 1 triyaj + 1 gözlem ----
    # "İkisi aynı alandan" = o alandan ambulansa çıkan sayısı 2. Tek eşitsizlikle:
    # ayni_alan >= (o alandan çıkan) - 1. C-009 katı kuralı ayrı ve bozulmuyor.
    kural = v.kural("O-008")
    if kural and kural.agirlik:
        cezalar = []
        vardiya_gunleri = {(g, vd) for (_p, g, vd, _gr) in t}
        for g, vardiya_kodu in sorted(vardiya_gunleri):
            for alan in ("TRIYAJ", "GOZLEM"):
                birlikte = []
                for p_id in kapsama_sayilan:
                    rozet = t.get((p_id, g, vardiya_kodu, alan))
                    amb = t.get((p_id, g, vardiya_kodu, "AMBULANS"))
                    if rozet is None or amb is None:
                        continue
                    ikisi = model.new_bool_var(f"o8_{alan}_{p_id}_{g}")
                    model.add(ikisi >= rozet + amb - 1)
                    birlikte.append(ikisi)
                if len(birlikte) < 2:
                    continue
                ayni = model.new_bool_var(f"o8_ayni_{alan}_{g}_{vardiya_kodu}")
                model.add(ayni >= sum(birlikte) - 1)
                cezalar.append(ayni)
        if cezalar:
            terimler.append((int(kural.agirlik), sum(cezalar)))
    return terimler


def _beklenen_yukler(v: SolverVerisi) -> dict[str, int]:
    """Adalet hedeflerinin payı: ihtiyaç ŞABLONUNUN yüklediği toplam iş.

    Ortalamayı çözümden değil şablondan hesaplıyoruz. Çözümden hesaplasaydık
    (a) bir bölme gerekirdi — CP-SAT tam sayıyla çalışır — ve (b) kapsama açığı
    olduğunda hedef kendiliğinden düşerdi, yani adaletsizlik ödüllendirilirdi.
    """
    yuk = {"saat": 0, "gece": 0, "hafta_sonu": 0, "ambulans": 0}
    for satir in v.ihtiyaclar:
        vardiya = next((vd for vd in v.vardiyalar if vd.kod == satir.vardiya_kodu), None)
        if vardiya is None:
            continue
        if satir.slot_kodu == "GENEL":
            yuk["saat"] += satir.min_sayi * len(satir.gunler) * vardiya.sure_yb
            if vardiya.gece_mi:
                yuk["gece"] += satir.min_sayi * len(satir.gunler)
            yuk["hafta_sonu"] += satir.min_sayi * sum(
                1 for g in satir.gunler if g.isoweekday() >= 6
            )
        elif any(y.kod == "AMBULANS" for y in satir.yetkinlikler):
            yuk["ambulans"] += satir.min_sayi * len(satir.gunler)
    return yuk


def _acil_takviye_degiskenleri(model, v: SolverVerisi, x: dict) -> dict:
    """C-022: oryantasyondaki kişinin genel mevcuda SAYILDIĞI atama kipi.

    Aynı kişi-gün-vardiya için iki kip var: normal (eğitim hemşiresinin yanında,
    mevcuda sayılmaz) ve TAKVİYE (eşsiz olabilir, mevcuda sayılır). Ayrı bir
    boole bunu işaretliyor; takviye ancak kişi o vardiyada çalışıyorsa açılabilir.

    Ambulans yasağı ayrı bir kısıt gerektirmiyor: oryantasyondakilere zaten hiç
    görev değişkeni açılmıyor (_gorev_degiskenleri kapsamaya sayılanlarla sınırlı),
    dolayısıyla ambulans rozeti de alamıyorlar. Aynı sebeple triyaj/gözlem yetkin
    sayımına da katılmıyorlar — istenen davranış bu.
    """
    if v.kural("C-022") is None:
        return {}
    takviye: dict[tuple[int, date, str], cp_model.IntVar] = {}
    for p in v.personel:
        if not p.oryantasyonda:
            continue
        for (p_id, g, vardiya_kodu), calisiyor in x.items():
            if p_id != p.id:
                continue
            tak = model.new_bool_var(f"takviye_{p_id}_{g}_{vardiya_kodu}")
            model.add(tak <= calisiyor)
            takviye[p_id, g, vardiya_kodu] = tak
    return takviye


def _gorev_degiskenleri(model, v: SolverVerisi, x: dict, kapsama_sayilan: set[int]) -> dict:
    """t[kişi, gün, vardiya, görev] — yalnız kind='TASK' yetkinlikler için.

    Hangi görevlerin var olduğu KODA YAZILMAZ: ihtiyaç şablonunun istediği
    TASK türü yetkinliklerden türer (bugün TRIYAJ, GOZLEM, AMBULANS).
    Değişken üç koşul birden doğruysa açılır: kişi o vardiyada çalışabiliyor,
    yetkinliği var, ve kapsamaya sayılıyor (sorumlu ile oryantasyondakilere
    hiçbir görev açılmaz — ekip mevcuduna sayılmadıkları için görev slotunu da
    dolduramazlar).
    """
    vardiya_gorevleri: dict[str, set[str]] = defaultdict(set)
    for satir in v.ihtiyaclar:
        for y in satir.yetkinlikler:
            if y.kind == "TASK":
                vardiya_gorevleri[satir.vardiya_kodu].add(y.kod)

    yetkinlik = {p.id: p.yetkinlikler for p in v.personel}
    t: dict[tuple[int, date, str, str], cp_model.IntVar] = {}
    for (p_id, g, vardiya_kodu), calisiyor in x.items():
        if p_id not in kapsama_sayilan:
            continue
        for gorev in vardiya_gorevleri.get(vardiya_kodu, ()):
            if gorev not in yetkinlik[p_id]:
                continue
            d = model.new_bool_var(f"t_{p_id}_{g}_{vardiya_kodu}_{gorev}")
            # Görev ancak kişi o vardiyada çalışıyorsa verilebilir (C-019).
            model.add(d <= calisiyor)
            t[p_id, g, vardiya_kodu, gorev] = d
    return t


def _gorev_kisitlari(model, v: SolverVerisi, x: dict, t: dict,
                     kapsama_sayilan: set[int], gevset, takviye: dict) -> None:
    """C-011, C-010, ayrıklık, tam bölme ve C-009."""
    yetkinlik = {p.id: p.yetkinlikler for p in v.personel}
    kalan_kural = v.kural("C-009").kod if v.kural("C-009") else None
    bolme_kural = "all_crew_triage_or_observation"

    # Görev satırları: TASK yetkinliği isteyen ihtiyaç satırları
    gorev_satirlari = [
        (satir, next(y.kod for y in satir.yetkinlikler if y.kind == "TASK"))
        for satir in v.ihtiyaclar
        if any(y.kind == "TASK" for y in satir.yetkinlikler)
    ]

    for satir, gorev in gorev_satirlari:
        # Satırın istediği TÜM yetkinlikler sayıma girer: C-011 hem TRIYAJ (TASK)
        # hem HASTA_ILT (QUALIFICATION) ister. Rozet TRIYAJ yetkinliği olan herkese
        # verilebilir ama sayıma yalnız ikisini de taşıyanlar girer —
        # v_daily_coverage tam olarak böyle sayıyor.
        istenen = {y.kod for y in satir.yetkinlikler}
        for g in satir.gunler:
            sayilanlar = [
                d for (p_id, gun, vardiya_kodu, gr), d in t.items()
                if gun == g and vardiya_kodu == satir.vardiya_kodu and gr == gorev
                and istenen <= yetkinlik[p_id]
            ]
            e = gevset(g, satir.vardiya_kodu, satir.slot_kodu, satir.min_sayi, satir.kural_kodu)
            model.add(sum(sayilanlar) + e >= satir.min_sayi)
            if gorev in TAM_SAYILI_GOREVLER:
                # Alt sınır gevşetilebilir (eksik kalabilir), üst sınır KATI.
                # O-005 adalet terimi olmasaydı rozet maliyeti zaten 2'de tutardı;
                # ama adalet (200) rozet maliyetini (1) ezip fazladan rozet yazıyordu.
                model.add(sum(sayilanlar) <= satir.min_sayi)

    # Ayrıklık + tam bölme. Veritabanı ayrıklığı zaten zorluyor (migration 011
    # trigger'ı source='solver' için HATA verir) — model uymazsa yazma patlar.
    rozetsizler: dict[tuple[date, str], list] = defaultdict(list)
    for (p_id, g, vardiya_kodu), calisiyor in x.items():
        if p_id not in kapsama_sayilan:
            continue
        tri = t.get((p_id, g, vardiya_kodu, "TRIYAJ"))
        goz = t.get((p_id, g, vardiya_kodu, "GOZLEM"))
        if tri is None and goz is None:
            continue
        if tri is not None and goz is not None:
            model.add(tri + goz <= 1)
        # Çalışıyorsa tam olarak bir rozet; çalışmıyorsa hiç.
        # rozetsiz: gevşeme — kural sağlanamazsa çizelge yine üretilsin.
        rozetsiz = model.new_bool_var(f"rozetsiz_{p_id}_{g}_{vardiya_kodu}")
        # CP-SAT değişkeni Python'da boolean olarak değerlendirilemez ("tri or 0"
        # çalışmaz) — var olan rozetleri açıkça listeliyoruz.
        rozetler = [d for d in (tri, goz) if d is not None]
        model.add(sum(rozetler) + rozetsiz == calisiyor)
        rozetsizler[g, vardiya_kodu].append(rozetsiz)

    # Rozetsiz kalanlar (gün, vardiya) başına tek sayaçta toplanır; amaç
    # fonksiyonuna görev açığı olarak o sayaç girer.
    for (g, vardiya_kodu), degiskenler in rozetsizler.items():
        e = gevset(g, vardiya_kodu, "ROZETSIZ", len(degiskenler), bolme_kural)
        model.add(e == sum(degiskenler))

    # C-009: ambulanstan sonra alanda kalan — KATI, hiçbir koşulda gevşemez.
    #
    # KURAL KATALOG KODUYLA OKUNUR, ihtiyaç satırının kuralından DEĞİL. Sebep:
    # seeds/016 ambulans satırını 'ambulance_crew_size'a bağladı; parametreler ise
    # C-009'da duruyor. Satırın kuralından okuyunca parametre bulunamıyor ve kısıt
    # SESSİZCE hiç kurulmuyordu (13 Kasım gecesi triyaj boş kaldı). Bağlantı
    # değişse bile kural yerinde kalsın diye artık katalog kodundan geliyor.
    kalan_kural = v.kural("C-009")
    kalanlar: dict[tuple[date, str], list] = {}
    if kalan_kural is not None:
        # Ambulans görevinin hangi gün ve vardiyalarda var olduğu ihtiyaç
        # satırlarından gelir; kısıt o kümede kurulur.
        ambulans_gunleri: set[tuple[date, str]] = set()
        for satir, gorev in gorev_satirlari:
            if gorev == "AMBULANS":
                ambulans_gunleri.update((g, satir.vardiya_kodu) for g in satir.gunler)

        for alan, param in (("TRIYAJ", "min_remaining_triage"),
                            ("GOZLEM", "min_remaining_observation")):
            if param not in kalan_kural.parametreler:
                continue
            asgari = int(kalan_kural.parametreler[param])
            for g, vardiya_kodu in sorted(ambulans_gunleri):
                alandakiler, ambulanstakiler = [], []
                for p_id in kapsama_sayilan:
                    rozet = t.get((p_id, g, vardiya_kodu, alan))
                    if rozet is None:
                        continue
                    alandakiler.append(rozet)
                    amb = t.get((p_id, g, vardiya_kodu, "AMBULANS"))
                    if amb is None:
                        continue
                    # "Hem bu alanda hem ambulansta" bir ÇARPIM. Tek eşitsizlikle
                    # doğrusallaştırıyoruz: ikisi de 1 ise 1'e zorlanır.
                    birlikte = model.new_bool_var(f"amb_{alan}_{p_id}_{g}")
                    model.add(birlikte >= rozet + amb - 1)
                    ambulanstakiler.append(birlikte)
                if not alandakiler:
                    continue
                # Gevşeme değişkeni YOK. Kadro yetmezse ambulans eksik kalır
                # (o slot gevşetilebilir), alan asla boşalmaz.
                kalan = sum(alandakiler) - sum(ambulanstakiler)
                model.add(kalan >= asgari)
                kalanlar.setdefault((g, vardiya_kodu), []).append(kalan)

    # C-022 (c): acil takviyeyle yazılan oryantasyondaki kişi alanda YALNIZ
    # kalmaz — ambulans çıktıktan sonra en az 1 yetkin kişi durmalı. C-009 her
    # alan için bunu zaten sağlıyor; burada toplam üzerinden bağlıyoruz ki
    # kadro çok daraldığında (alanlar boşaldığında) takviye de kapansın.
    for (g, vardiya_kodu), kalan_ifadeler in kalanlar.items():
        tak = [d for (_p, gun, kod), d in takviye.items()
               if gun == g and kod == vardiya_kodu]
        if tak:
            model.add(sum(tak) <= sum(kalan_ifadeler))


def _yetkinlik_slotlari(model, v: SolverVerisi, x: dict,
                        sorumlu_plani: list[tuple[int, date, str]], gevset) -> None:
    """SAYIM ve SHIFT_YETKILISI: görev değil, kişinin taşıdığı YETKİ.

    Rozet yok; soru "o vardiyada bu yetkiye sahip biri çalışıyor mu". Sorumlu
    hemşire ve oryantasyondakiler BURADA SAYILIR: v_daily_coverage'ta hariç tutma
    yalnız yetkinlik şartı olmayan satıra (GENEL) uygulanıyor. seeds/008 de bunu
    açıkça söylüyor ("sorumlu hemşire de sayabilir").
    """
    yetkinlik = {p.id: p.yetkinlikler for p in v.personel}
    sabitler: Counter[tuple[date, str]] = Counter()
    for p_id, g, vardiya_kodu in sorumlu_plani:
        sabitler[g, vardiya_kodu, p_id] = 1
    for sa in v.sabit_atamalar:
        sabitler[sa.gun, sa.vardiya_kodu, sa.personel_id] = 1

    for satir in v.ihtiyaclar:
        if not satir.yetkinlikler or any(y.kind == "TASK" for y in satir.yetkinlikler):
            continue                                   # GENEL ya da görev satırı
        istenen = {y.kod for y in satir.yetkinlikler}
        for g in satir.gunler:
            adaylar = [
                d for (p_id, gun, vardiya_kodu), d in x.items()
                if gun == g and vardiya_kodu == satir.vardiya_kodu and istenen <= yetkinlik[p_id]
            ]
            hazir = sum(
                1 for (gun, vardiya_kodu, p_id) in sabitler
                if gun == g and vardiya_kodu == satir.vardiya_kodu and istenen <= yetkinlik[p_id]
            )
            e = gevset(g, satir.vardiya_kodu, satir.slot_kodu, satir.min_sayi, satir.kural_kodu)
            model.add(sum(adaylar) + hazir + e >= satir.min_sayi)


def _sorumlu_plani(v: SolverVerisi, engelli: set[tuple[int, date]]) -> list[tuple[int, date, str]]:
    """C-008: hafta içi gündüz, Cumartesi kısa vardiya, Pazar izinli. Seçim değil, sabit girdi."""
    sorumlu = next((p for p in v.personel if p.rol_kodu == SORUMLU_ROL), None)
    if sorumlu is None:
        return []
    mevcut = {s.kod for s in v.vardiyalar}
    plan = []
    for g in v.gunler:
        if (sorumlu.id, g) in engelli:
            continue
        isodow = g.isoweekday()
        kod = "GUNDUZ" if isodow <= 5 else (SORUMLU_CUMARTESI if isodow == 6 else None)
        if kod and kod in mevcut:
            plan.append((sorumlu.id, g, kod))
    return plan


def _sabit_kapsama_sayimi(v: SolverVerisi) -> Counter[tuple[date, str]]:
    """Sabit satırlardan kapsamaya SAYILAN kişiler — v_daily_coverage ile aynı kural."""
    sayilan = {p.id for p in v.personel if p.kapsamaya_sayilir}
    return Counter(
        (s.gun, s.vardiya_kodu) for s in v.sabit_atamalar if s.personel_id in sayilan
    )


def _durumu_cevir(durum: int) -> SolverStatus:
    if durum == cp_model.OPTIMAL:
        return "OPTIMAL"
    if durum == cp_model.FEASIBLE:
        return "FEASIBLE"
    if durum == cp_model.INFEASIBLE:
        return "INFEASIBLE"
    return "HATA"


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------


def _kosuyu_bul_veya_ac(cur, draft_id: int, time_limit_s: int) -> int:
    cur.execute(
        """SELECT id FROM solver_runs
            WHERE draft_id = %s AND status = 'CALISIYOR'
            ORDER BY started_at DESC LIMIT 1""",
        (draft_id,),
    )
    if (satir := cur.fetchone()) is not None:
        return satir["id"]
    cur.execute(
        """INSERT INTO solver_runs (draft_id, status, time_limit_seconds)
           VALUES (%s, 'CALISIYOR', %s) RETURNING id""",
        (draft_id, time_limit_s),
    )
    return cur.fetchone()["id"]


def _atamalari_yaz(cur, draft_id: int, v: SolverVerisi, cozum: Cozum) -> int:
    """Dönem içinde YALNIZ source='manuel' ya da is_locked satırlar sabittir.

    'referans' bir başlangıç kopyasıdır (kağıttan/başka taslaktan), kullanıcı kararı
    değil — 'solver' ile birlikte silinir ve yeniden üretilir. Dönem dışı satırlara
    ('onceki_ay' bağlamı) hiç dokunulmaz.
    """
    cur.execute(
        """
        DELETE FROM assignments a
        USING schedule_drafts d
        WHERE a.draft_id = %s AND d.id = a.draft_id
          AND d.period @> a.work_date
          AND a.source IN ('solver', 'referans')
          AND NOT a.is_locked
        """,
        (draft_id,),
    )
    vardiya_id = {s.kod: s.id for s in v.vardiyalar}
    cur.executemany(
        """
        INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source)
        VALUES (%s, %s, %s, %s, 'solver')
        ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING
        """,
        [(draft_id, p_id, vardiya_id[kod], g) for p_id, g, kod in cozum.atamalar],
    )
    _rozetleri_yaz(cur, draft_id, cozum)
    cur.execute(
        "SELECT count(*) AS adet FROM assignments WHERE draft_id = %s AND source = 'solver'",
        (draft_id,),
    )
    return cur.fetchone()["adet"]


def _rozetleri_yaz(cur, draft_id: int, cozum: Cozum) -> None:
    """Görev rozetlerini assignment_tasks'a yazar.

    Eski rozetler assignments silinirken ON DELETE CASCADE ile gitti, ayrı DELETE yok.
    Yetkinlik trigger'ı (migration 010) güvenlik ağı: değişkenler zaten yalnız
    yetkinliği olanlara açıldığı için tetiklenmemeli — tetiklenirse modelde hata
    var demektir ve koşu HATA ile kapanır.
    """
    if not cozum.rozetler:
        return
    cur.execute(
        """SELECT id, staff_id, work_date FROM assignments
            WHERE draft_id = %s AND source = 'solver'""",
        (draft_id,),
    )
    atama_id = {(r["staff_id"], r["work_date"]): r["id"] for r in cur.fetchall()}

    cur.execute("SELECT id, code FROM competencies")
    yetkinlik_id = {r["code"]: r["id"] for r in cur.fetchall()}

    cur.executemany(
        """INSERT INTO assignment_tasks (assignment_id, competency_id)
           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
        [
            (atama_id[p_id, g], yetkinlik_id[gorev])
            for p_id, g, _vardiya, gorev in cozum.rozetler
            if (p_id, g) in atama_id
        ],
    )


def _teshisleri_yaz(cur, run_id: int, v: SolverVerisi, cozum: Cozum) -> int:
    """Eksikler, 200 saate ulaşamayanlar ve karşılanamayan istekler — hepsi
    sade Türkçe açıklamayla. Cümleleri solver/aciklama.py kuruyor."""
    cur.execute("DELETE FROM solver_diagnostics WHERE solver_run_id = %s", (run_id,))
    satirlar = (
        aciklama.eksik_aciklamalari(v, cozum, run_id)
        + aciklama.saat_aciklamalari(v, cozum, run_id)
        + aciklama.istek_aciklamalari(v, cozum, run_id)
        + aciklama.takviye_aciklamalari(v, cozum, run_id)
    )
    if satirlar:
        cur.executemany(
            """
            INSERT INTO solver_diagnostics
                (solver_run_id, severity, constraint_id, work_date, message, suggestion)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            satirlar,
        )
    return len(satirlar)


def _kontrolcuyu_calistir(cur, run_id: int, draft_id: int, v: SolverVerisi) -> int:
    """Her çözümden sonra bağımsız kontrolcüyü koşturur.

    NEDEN: C-009'un "alanda kalan" kuralı seeds/016'da bir bağlantı değişince
    SESSİZCE kurulmaz oldu ve bunu ancak haftalar sonra, ekrana bakarken fark
    ettik. Kontrolcü zaten vardı ama elle çağrılıyordu. Artık her koşu kendi
    sonucunu denetliyor; katı bir kural ihlal edilmişse E-10'un en üstünde
    kırmızı görünür.

    Yalnız KATI kurallar 'hata' sayılır. Gevşetilebilir slot eksikleri (triyaj
    sayısı, ambulans mevcudu …) kadro yetmediğinde beklenen davranıştır ve solver
    onları zaten kendi teşhisinde bildirir.
    """
    from solver import validate

    try:
        bulgular = validate.kontrol_et(v, validate.atamalari_oku(draft_id))
        ihlaller = [i for i in bulgular if i.kati]
        uyarilar = [i for i in bulgular if i.seviye == "uyari"]
    except Exception as hata:  # noqa: BLE001 — kontrolcü çökerse çözüm kaybolmasın
        cur.execute(
            """INSERT INTO solver_diagnostics (solver_run_id, severity, message, suggestion)
               VALUES (%s, 'hata', %s, %s)""",
            (run_id, f"Kontrolcü çalıştırılamadı: {hata}",
             "Çizelge yazıldı ama denetlenemedi. solver/validate.py'yi elle koşturun."),
        )
        return 1
    kod_id_u = {k.katalog_kodu: k.id for k in v.kurallar.values() if k.katalog_kodu}
    if uyarilar:
        cur.executemany(
            """INSERT INTO solver_diagnostics
                 (solver_run_id, severity, constraint_id, work_date, message, suggestion)
               VALUES (%s, 'uyari', %s, %s, %s, %s)""",
            [(run_id, kod_id_u.get(i.kod), i.gun,
              f"{i.personel}: {i.aciklama}",
              "Elle yapılmış istisna. Kasıtlıysa bir şey yapmanıza gerek yok.")
             for i in uyarilar[:20]],
        )
    if not ihlaller:
        return len(uyarilar[:20])

    kod_id = {k.katalog_kodu: k.id for k in v.kurallar.values() if k.katalog_kodu}
    satirlar = [(
        run_id, "hata", None, None,
        f"Kontrolcü {len(ihlaller)} katı kural ihlali buldu — çizelge güvenilir değil.",
        "Bu bir model hatasıdır: solver kurala uymayan bir çizelge üretti."
        " Aşağıdaki kalemlere bakın.",
    )]
    for i in ihlaller[:20]:
        satirlar.append((
            run_id, "hata", kod_id.get(i.kod), i.gun,
            f"{i.kod} {i.kural} — {i.personel}: {i.aciklama}",
            "Katı kural ihlali.",
        ))
    cur.executemany(
        """INSERT INTO solver_diagnostics
             (solver_run_id, severity, constraint_id, work_date, message, suggestion)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        satirlar,
    )
    return len(satirlar) + len(uyarilar[:20])


def _parametre_fotografi(v: SolverVerisi, cozum: Cozum) -> dict:
    """'solver': 'cpsat' arayüzdeki "Referans kopya (solver değil)" etiketini kaldırır."""
    return {
        "solver": "cpsat",
        "adim": 5,
        "kapsanan_kurallar": ["C-002", "C-003", "C-004", "C-005", "C-006", "C-007",
                              "C-008", "C-009", "C-010", "C-011", "C-014", "C-016",
                              "C-017", "C-019", "C-020", "C-021", "O-001", "O-002",
                              "O-003", "O-004", "O-005",
                              "all_crew_triage_or_observation",
                              "count_authority_required"],
        "kapsam_disi": ["C-013"],
        "agirliklar": {"eksik_cezasi_yedek": EKSIK_CEZASI_YEDEK,
                       "saat_eksigi_cezasi": SAAT_EKSIGI_CEZASI,
                       "atama_maliyeti": ATAMA_MALIYETI, "rozet_maliyeti": ROZET_MALIYETI},
        "adalet_hedefleri": cozum.hedefler,
        "cozucu": {"tohum": RASTGELE_TOHUM, "isci": get_settings().solver_workers},
        "sorumlu_cumartesi": SORUMLU_CUMARTESI,
        "erken_durdu": cozum.erken_durdu,
        "durgunluk_s": cozum.durgunluk_s,
        "model": {"degisken": cozum.degisken_sayisi,
                  "gorev_degiskeni": cozum.gorev_degiskeni, "kisit": cozum.kisit_sayisi,
                  "cozum_suresi_s": round(cozum.cozum_suresi, 3)},
        "kurallar": [
            {"code": k.kod, "catalog_code": k.katalog_kodu, "is_hard": k.hard_mi,
             "weight": k.agirlik,
             "parametreler": {a: float(d) for a, d in k.parametreler.items()}}
            for k in v.kurallar.values()
        ],
    }
