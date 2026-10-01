"""CP-SAT çözücü — ADIM 5: adalet ve 200 saat.

Adım 2'den devralınan: günde en fazla 1 vardiya, izin/kesin istek günleri boş,
C-017 (sadece gündüzcüler geceye yazılmaz), C-008 (sorumlunun sabit programı),
C-005/C-006 genel mevcut (GEVŞETİLEBİLİR: eksik kalırsa büyük ceza, çizelge yine üretilir).

Adım 3'ün eklediği KATI kurallar — parametreleri veritabanından okunur:
  C-002  en fazla 2 gece arka arkaya
  C-014  2 gece arka arkaya çalışan ertesi gün hiç çalışmaz
  C-021  gece çalışan ertesi gün gündüze yazılmaz          (seeds/014)
  C-016  her Pzt–Paz haftasında en az 1 boş gün
  C-023  gündüzcü haftada TAM 1 gün izin yapar
  C-024  üst üste en fazla 2 izinsiz boş gün
  C-025  karma hafta: gündüz+gece personelde haftada en az 1 gündüz + 1 gece
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
  O-001  fazla mesai (haftalık BRÜT 51 sa üstü) · O-009 günlük mevcut dengesi

30.09 eklenenleri (seeds/034) — çalışma süresi:
  C-026  haftalık yasal asgari NET 45 sa · C-027 aylık yasal asgari NET 180 sa
  C-028  haftada en az 5 gün çalışma, en fazla 2 gün izin

ZORUNLU / ESNEK DÜĞMESİ (E-03) HER KURALDA İŞLER: kural `is_hard` ise kısıt,
değilse ağırlığıyla cezalı tercih (bkz. _KuralUygulayici). Eskiden zorunlu yapılan
esnek kural ağırlığı boşaldığı için SESSİZCE devre dışı kalıyordu.

İŞLENMİŞ GÜNLER: dönem içinde başka bir yayınlanmış çizelgenin kapsadığı günler
(ör. kağıt haftadan gelen 1–4 Ekim) taslağa kilitli kopyalanır, değişken açılmaz;
haftalık kurallar o günleri sabit değer olarak görür ve kalan günleri ona göre kurar.

BİRİM ÖLÇEĞİ burada, veritabanında değil: ağırlıklar "yarım saat başına ceza"
anlamındadır, gece/hafta sonu sayıları vardiya süresiyle çarpılarak yarım saate
çevrilir. Veritabanındaki sayı saf ÖNCELİKTİR.

Bu adımda BİLEREK YOK: C-013 uyumsuz kişi cezası (veri yok).
"""

from __future__ import annotations

import calendar
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

# BİRİM ÖLÇEĞİ — 29.09.2026'da modelin zaman birimi yarım saatten DAKİKAYA geçti
# (molalar mesaiden çıkınca gündüzün neti 490 dk oldu, yarım saatin katı değil).
#
# Amaç fonksiyonu iki tür terim karıştırıyor: ZAMAN taşıyanlar (saat eksiği,
# fazla mesai, saat adaleti, haftalık referans) ve SAYI taşıyanlar (kapsama
# eksiği, atama maliyeti, ambulans adaleti, karşılanmayan istek). Veritabanındaki
# ağırlıklar "yarım saat başına ceza" olarak yazılmıştı. Birimi dakikaya
# çevirince zaman terimleri kendiliğinden 30 kat ağırlaşır ve kapsama eksiği
# göreli olarak 30 kat ucuzlar — solver bir vardiyayı boş bırakmayı tercih
# etmeye başlardı.
#
# Çözüm: SAYI taşıyan terimlerin ağırlığı bu çarpanla yükseltiliyor. Bölme
# yapamıyoruz (CP-SAT tam sayıyla çalışır ve değişken bölünemez), o yüzden
# amacın TAMAMI 30 ile ölçekleniyor. Terimler arası oranlar birebir korunur;
# yalnız raporlanan amaç değeri 30 kat büyür.
YB_DK = 30


def _sayi(agirlik: int) -> int:
    """Zaman TAŞIMAYAN bir terimin ağırlığını model ölçeğine çevirir (bkz. YB_DK)."""
    return int(agirlik) * YB_DK

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

# C-008 (sorumlunun Pzt–Cum gündüz, Cmt kısa, Paz izin programı) artık KODDA DEĞİL:
# staff_weekly_patterns'ta veri (migration 024 + seeds/031). Program değişirse
# burası değişmez. Kağıda dönmek istenirse Cumartesi satırının shift_type_id'si
# GUNDUZ'a çekilir, tek UPDATE.

# C-016 bir haftanın kaç gününü bilirsek kuralı uygularız. Dönemin ucundaki yarım
# haftada bilinen gün sayısı azaldıkça kural anlamını yitirir: bir haftanın yalnız
# 1 günü dönem içindeyse "o haftada 1 boş gün olsun" o TEK günü boşaltmak demektir
# ve kimse çalışamaz (30 Kasım 2026 Pazartesi tam böyleydi). Kişi dinlenme gününü
# haftanın bilmediğimiz kısmında kullanabilir. Haftanın çoğunluğunu (4 gün)
# biliyorsak kuralı uyguluyoruz.
C016_ASGARI_BILINEN_GUN = 4

# Geçmişe bakış penceresi (gün). En uzun geri bakış C-016'nın haftasıdır.
GECMIS_GUN = 7

# KATI kuralın ACİL gevşemesi. Yeni haftalık kurallar (C-025–C-028) geçmişe ve
# işlenmiş günlere bakıyor; geçmiş zaten kuralı bozmuşsa ya da kesin izin
# istekleri haftayı imkânsız kılıyorsa düz kısıt modeli ÇÖZÜMSÜZ bırakır ve
# hiç çizelge çıkmaz. Bunun yerine bu cezayla gevşer: kapsama eksiğinden
# (2.000.000 × 30) bile pahalı, yani solver ancak gerçekten imkânsızsa kullanır.
# Kullanıldığında kontrolcü 'hata' olarak raporlar — sessiz kalmaz.
ACIL_CEZA = 1_000_000_000

# Eğitim hemşiresi oryantasyondaki eşi OLMADAN çalıştığında (eşi dinleniyor)
# gün başına ceza. Kapsama eksiğinin (2.000.000) altında, istek cezasının
# (22.000) üstünde: gerektiğinde olur, keyfî olmaz.
GOLGE_CEZASI = 100_000


def run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult:
    baslangic = time.monotonic()
    settings = get_settings()
    # İşlenmiş günler (başka yayından gelen) okuma ÖNCESİ taslağa kilitli yazılır:
    # veri okuyucu onları sabit atama olarak görür.
    _islenmis_gunleri_esitle(draft_id)
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
                # Atamalar ÖNCE commit edilir (kontrolcü kendi bağlantısıyla okur),
                # koşunun durumu ise kontrolcü BİTTİKTEN sonra yazılır: arayüz
                # "çözüldü"yü gördüğünde atamalar da teşhisler de yerinde olsun
                # (01.10: "çözüldü" yazısı vardiyalardan önce geliyordu).
                conn.commit()
                teshis_sayisi += _kontrolcuyu_calistir(cur, run_id, draft_id, veri)
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
    islenmis = v.islenmis_gunler
    # Solver'ın KARAR verebildiği dönem günleri. Zaman kurallarının "pencerede
    # dönem günü var mı" korumaları buna bakar: tamamen işlenmiş bir pencere
    # geçmiş gibidir, değiştirilemez.
    serbest_donem = set(v.gunler) - islenmis

    # Haftanın 7 günü de deseninde bağlı olan kişinin seçeneği yok (bugün yalnız
    # sorumlu hemşire, C-008) → değişkeni açılmaz, planı girdi olarak yazılır.
    # Kimin sabit olduğu staff_weekly_patterns'tan gelir, roldan DEĞİL (migration 024).
    # Oryantasyondakiler ATANIYOR (C-020 onları eşine bağlıyor), kapsamaya sayılmıyorlar.
    atanabilirler = [p for p in v.personel if not p.sabit_programli]
    kapsama_sayilan = {p.id for p in v.personel if p.kapsamaya_sayilir}

    # ----- Değişkenler -----
    # İmkânsız üçlü için değişken AÇILMIYOR: model küçülür ve "değişken yok"
    # ihlal edilmesi imkânsız bir kuraldır.
    x: dict[tuple[int, date, str], cp_model.IntVar] = {}
    for p in atanabilirler:
        for g in v.gunler:
            if g not in p.calisabilir_gunler:
                continue          # sözleşmesi o günü kapsamıyor (ayrılmış / henüz başlamamış)
            if (p.id, g) in engelli or g in islenmis:
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

    sabit_plan = _sabit_desen_plani(v, engelli | {(p.id, g) for p in v.personel for g in islenmis})
    uygulayici = _KuralUygulayici(model)

    # ----- Zaman çizgisi: geçmiş + dönem -----
    gece, gunduz, calisiyor, tum_gunler, net, brut = _zaman_cizgisi(v, x, sabit_plan)
    donem = serbest_donem

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
    kisiler = atanabilirler + [p for p in v.personel if p.sabit_programli]
    _ardisik_gece(uygulayici, v, kisiler, gece, tum_gunler, donem)              # C-002
    _iki_gece_sonrasi_bos(uygulayici, v, kisiler, gece, calisiyor, tum_gunler, donem)  # C-014
    _gece_sonrasi_gunduz_yok(uygulayici, v, kisiler, gece, gunduz, tum_gunler, donem)  # C-021
    _haftalik_bos_gun(uygulayici, v, kisiler, calisiyor, tum_gunler, donem)     # C-016
    _gunduzcu_haftalik_off(uygulayici, v, atanabilirler, calisiyor, engelli, donem)  # C-023
    _ardisik_off_siniri(uygulayici, v, atanabilirler, calisiyor, engelli, tum_gunler, donem)  # C-024
    _off_penceresi(model, v, atanabilirler, calisiyor, engelli, donem)    # OFF_OLABILIR
    golge_cezalari = _oryantasyon_esi(model, v, x, takviye, engelli)      # C-020

    # ----- Çalışma süresi (seeds/034) -----
    haftalik = _HaftaBaglami(v, x, tum_gunler, donem, yok, bos,
                             calisiyor, gece, gunduz, net, brut, model)
    _karma_hafta(uygulayici, v, haftalik)                                       # C-025
    _haftalik_yasal_saat(uygulayici, v, haftalik)                               # C-026
    _haftalik_calisma_gunu(uygulayici, v, haftalik)                             # C-028
    fazla_mesai = _fazla_mesai(model, v, haftalik)                         # O-001, O-010

    # ----- Görevler (Adım 4) -----
    t = _gorev_degiskenleri(model, v, x, kapsama_sayilan)
    sonuc.gorev_degiskeni = len(t)
    _gorev_kisitlari(model, v, x, t, kapsama_sayilan, gevset, takviye)
    _yetkinlik_slotlari(model, v, x, sabit_plan, gevset)

    # ----- Amaç -----
    # Atama maliyeti yalnız kapsamaya SAYILAN kişilere: maliyetin amacı ekibi
    # şişirmemek. Oryantasyondakilere uygulanırsa eğitim hemşiresini kullanmak
    # 3 birim eder ve solver onu kullanmaktan kaçınır — kural ters teper.
    ekip_atamalari = [d for (p_id, _g, _k), d in x.items() if p_id in kapsama_sayilan]
    ambulans_rozetleri = [d for (_p, _g, _v, gorev), d in t.items() if gorev == "AMBULANS"]
    # Her eksik KENDİ kuralının ağırlığıyla cezalanır (seeds/016 kademeleri).
    # Hepsi SAYI taşır (adet), zaman değil → _sayi() ile ölçekleniyor.
    temel: list[tuple[int, object]] = [
        (_sayi(ATAMA_MALIYETI), sum(ekip_atamalari)),
        (_sayi(ROZET_MALIYETI), sum(ambulans_rozetleri)),
    ]
    for (_g, _vd, _slot), (e, kural_kodu, _n) in eksik.items():
        kural = v.kurallar.get(kural_kodu) if kural_kodu else None
        temel.append((_sayi(kural.agirlik) if kural and kural.agirlik
                      else _sayi(EKSIK_CEZASI_YEDEK), e))
    takviye_kural = v.kural("C-022")
    if takviye and takviye_kural and takviye_kural.agirlik:
        temel.append((_sayi(takviye_kural.agirlik), sum(takviye.values())))

    # Adalet havuzu kapsama havuzundan AYRI: ayrılan ve ay içinde başlayan personel
    # sahada mevcuda sayılır ama ayın tamamını çalışmadığı için saat/gece/hafta sonu
    # adaletine ve 200 saate girmez (hastane kararı). Bkz. Personel.adalete_girer.
    adalet_havuzu = {p.id for p in v.personel if p.adalete_girer}
    adalet_terimleri, olcumler = _adalet_ve_saat(model, v, x, t, adalet_havuzu, uygulayici)
    adalet_terimleri += fazla_mesai
    adalet_terimleri += _gunluk_denge(model, v, x, kapsama_sayilan, sabit_kapsama, donem)  # O-009
    adalet_terimleri += uygulayici.cezalar
    adalet_terimleri += golge_cezalari
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
        sonuc.atamalar += list(sabit_plan)
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
    vardiya = {s.kod: s for s in v.vardiyalar}
    gece_p: dict[tuple[int, date], list] = defaultdict(list)
    gunduz_p: dict[tuple[int, date], list] = defaultdict(list)
    net_p: dict[tuple[int, date], list] = defaultdict(list)
    brut_p: dict[tuple[int, date], list] = defaultdict(list)

    # Gece mi, kaç dakika: SATIRIN KENDİ vardiyasından. Pasif vardiyalar (GECE_0100)
    # v.vardiyalar'da yok ama işlenmiş günlerde ve geçmişte bulunabilir; koda
    # bakarak karar verseydik 01:00 çıkışlı gece "gündüz" sayılırdı.
    def ekle(p_id: int, g: date, gece_mi: bool, net_dk: int, brut_dk: int, deger) -> None:
        (gece_p if gece_mi else gunduz_p)[p_id, g].append(deger)
        net_p[p_id, g].append(deger * net_dk)
        brut_p[p_id, g].append(deger * brut_dk)

    for (p_id, g, kod), degisken in x.items():
        s = vardiya[kod]
        ekle(p_id, g, s.gece_mi, s.sure_dk, s.brut_dk, degisken)
    for p_id, g, kod in sorumlu_plani:
        s = vardiya[kod]
        ekle(p_id, g, s.gece_mi, s.sure_dk, s.brut_dk, 1)
    for s in v.sabit_atamalar:
        ekle(s.personel_id, s.gun, s.gece_mi, s.sure_dk, s.brut_dk, 1)
    for a in v.gecmis:                                   # değiştirilemez geçmiş
        ekle(a.personel_id, a.gun, a.gece_mi, a.sure_dk, a.brut_dk, 1)

    gece = lambda p_id, g: sum(gece_p.get((p_id, g), []))        # noqa: E731
    gunduz = lambda p_id, g: sum(gunduz_p.get((p_id, g), []))    # noqa: E731
    calisiyor = lambda p_id, g: gece(p_id, g) + gunduz(p_id, g)  # noqa: E731
    net = lambda p_id, g: sum(net_p.get((p_id, g), []))          # noqa: E731
    brut = lambda p_id, g: sum(brut_p.get((p_id, g), []))        # noqa: E731

    ilk = v.donem_bas - timedelta(days=GECMIS_GUN)
    tum_gunler = [ilk + timedelta(days=i) for i in range((v.gunler[-1] - ilk).days + 1)]
    return gece, gunduz, calisiyor, tum_gunler, net, brut


def _ardisik_gece(kural, v: SolverVerisi, kisiler, gece, tum_gunler, donem) -> None:
    """C-002: n+1 günlük her pencerede en fazla n gece."""
    k = v.kural("C-002")
    if k is None:
        return
    n = int(k.parametreler["max_consecutive_nights"])
    for p in kisiler:
        for i in range(len(tum_gunler) - n):
            pencere = tum_gunler[i:i + n + 1]
            # Tamamı geçmişte kalan pencere DEĞİŞTİRİLEMEZ; kısıt yazmak modeli
            # geçmişteki bir ihlal yüzünden çözümsüz yapardı.
            if not any(g in donem for g in pencere):
                continue
            kural.en_fazla(k, sum(gece(p.id, g) for g in pencere), n)


def _iki_gece_sonrasi_bos(kural, v: SolverVerisi, kisiler, gece, calisiyor, tum_gunler, donem) -> None:
    """C-014: n gece arka arkaya çalışıldıysa ertesi gün hiç çalışılmaz.

    'n gece + o gün çalışma ≤ n' okunuşu: geceler doluysa toplam zaten n'dir,
    o hâlde ertesi günün çalışma göstergesi 0 olmak zorunda.
    rest_gap_hours=24 ile birebir: ikinci gece d+2'de 08:30'da biter, 24 saat
    sonrası d+3'ün 08:30'u — yani d+2 tamamen boş, d+3 gündüzü serbest.
    """
    k = v.kural("C-014")
    if k is None:
        return
    n = int(k.parametreler["rest_trigger_nights"])
    for p in kisiler:
        for i in range(len(tum_gunler) - n):
            geceler = tum_gunler[i:i + n]
            ertesi = tum_gunler[i + n]
            if ertesi not in donem:          # sonuç günü dönem dışındaysa yapacak bir şey yok
                continue
            kural.en_fazla(k, sum(gece(p.id, g) for g in geceler) + calisiyor(p.id, ertesi), n)


def _gece_sonrasi_gunduz_yok(kural, v: SolverVerisi, kisiler, gece, gunduz, tum_gunler,
                             donem) -> None:
    """C-021: gece 08:30'da biter, gündüz 08:30'da başlar — ikisi arka arkaya olamaz."""
    k = v.kural("C-021")
    if k is None:
        return
    for p in kisiler:
        for i in range(len(tum_gunler) - 1):
            g, ertesi = tum_gunler[i], tum_gunler[i + 1]
            if ertesi not in donem:
                continue
            kural.en_fazla(k, gece(p.id, g) + gunduz(p.id, ertesi), 1)


def _haftalik_bos_gun(kural, v: SolverVerisi, kisiler, calisiyor, tum_gunler, donem) -> None:
    """C-016: her Pzt–Paz haftasında en az 1 boş gün (o gün başlayan vardiya yok).

    BİLİNEN gün = dönem içi ya da geçmiş penceresinde. Bunun dışındaki günler
    (örn. 1 Kasım) hesaba girmez. Ay başındaki yarım hafta geçmiş günlerle
    tamamlanır; dönem sonundaki yarım haftada kural bilinen günlere uygulanır.

    MUAFİYET: sabit programlı kişi dönem sonundaki yarım haftada muaftır —
    dinlenme günü (sorumlu hemşirede Pazar) dönemin dışına düşüyor, kuralı
    pencereye sıkıştırmak sabit programı yapay olarak bozardı. Kimin sabit
    olduğu desenden gelir, rolden değil (migration 024).
    """
    k = v.kural("C-016")
    if k is None:
        return
    en_az = int(k.parametreler["weekly_min_rest_events"])
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
        if not any(g in donem for g in gunler):
            continue                                       # hafta tamamen işlenmiş
        tam_hafta = len(gunler) == 7
        for p in kisiler:
            if not tam_hafta and p.sabit_programli:
                continue                                   # muafiyet
            kural.en_fazla(k, sum(calisiyor(p.id, g) for g in gunler), len(gunler) - en_az)


def _tam_haftalar(v: SolverVerisi) -> list[list[date]]:
    """Dönemin İÇİNDE tamamen kalan Pzt–Paz takvim haftaları.

    Hafta Pazartesi–Pazar (Edem teyidi, 29.09) — kayan 7 gün değil. Ay başı ve
    sonundaki yarım haftalar DIŞARIDA: "haftada tam 1 izin" yarım haftada
    anlamsız, uygulanırsa kaçınılmaz bir ihlal üretir.
    """
    donem = set(v.gunler)
    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        haftalar.setdefault(pzt, [pzt + timedelta(days=i) for i in range(7)])
    return [gunler for gunler in haftalar.values() if set(gunler) <= donem]


def _serbest_gun_mu(p, g: date, engelli: set[tuple[int, date]]) -> bool:
    """Kişinin o gün çalışıp çalışmamasını SOLVER seçebiliyor mu.

    İzin, rapor ve KESIN 'boş gün' isteği `engelli`de; onlar kuralın dışında
    (Edem: "istisna yıllık izin, rapor, planlayıcının girdiği kesin off").
    Sözleşmesi o günü kapsamıyorsa da seçim yok.
    """
    return (p.id, g) not in engelli and g in p.calisabilir_gunler


def _gunduzcu_haftalik_off(kural, v: SolverVerisi, kisiler, calisiyor,
                           engelli: set[tuple[int, date]], donem) -> None:
    """C-023: sadece gündüz çalışan personel haftada TAM 1 gün izin yapar.

    "En az 1" değil TAM: Edem'in kuralı "haftada 1 off, 2 ya da 3 değil".
    C-016 zaten en az 1 diyordu; bu kural üst sınırı da koyuyor.

    Gece de çalışabilen personele UYGULANMAZ — onların izni 1-2 günlük bloklar
    halinde (C-024), gece sonrası dinlenme de araya giriyor.

    Yalnız SERBEST günler sayılır: izinli/raporlu gün zaten boş, onu "haftalık
    izin" saymak kişiyi o hafta 6 gün çalışmaya zorlardı.
    """
    k = v.kural("C-023")
    if k is None:
        return
    adet = int(k.parametreler["day_only_weekly_off"])

    for gunler in _tam_haftalar(v):
        if not any(g in donem for g in gunler):
            continue                                       # hafta tamamen işlenmiş
        for p in kisiler:
            if p.uygunluk != "sadece_gunduz":
                continue
            serbest = [g for g in gunler if _serbest_gun_mu(p, g, engelli)]
            # Hafta izinle doluysa kural konmaz: kişi zaten çalışmıyor.
            if len(serbest) < len(gunler):
                continue
            kural.esit(k, sum(calisiyor(p.id, g) for g in serbest), len(serbest) - adet)


def _ardisik_off_siniri(kural, v: SolverVerisi, kisiler, calisiyor,
                        engelli: set[tuple[int, date]], tum_gunler, donem) -> None:
    """C-024: üst üste en fazla 2 izinsiz boş gün.

    3 gün üst üste boşluk kullanılmıyor. Kayan pencere: ardışık (sınır+1) günün
    en az 1'inde çalışılır.

    İzinli/raporlu günler pencereyi BOZMAZ, sadece kuralın dışında kalır —
    "istisna: yıllık izin, rapor, kesin off istekleri bloğu uzatabilir" (Edem).
    Penceresinde böyle bir gün varsa kısıt konmaz; o blok meşrudur.
    """
    k = v.kural("C-024")
    if k is None:
        return
    sinir = int(k.parametreler["max_consecutive_off"])
    pencere = sinir + 1

    for p in kisiler:
        for i in range(len(tum_gunler) - pencere + 1):
            dilim = tum_gunler[i:i + pencere]
            # Pencerenin tamamı bilinen ve seçilebilir günlerden oluşmalı.
            if not any(g in donem for g in dilim):
                continue
            if not all(_serbest_gun_mu(p, g, engelli) or g not in donem for g in dilim):
                continue
            # Geçmiş günler sabit; onlarda çalışılmışsa kısıt kendiliğinden sağlanır.
            kural.en_az(k, sum(calisiyor(p.id, g) for g in dilim), 1)


def _off_penceresi(model, v: SolverVerisi, kisiler, calisiyor,
                   engelli: set[tuple[int, date]], donem) -> None:
    """OFF_OLABILIR: kişinin haftalık izni yalnız belirli günlere düşebilir.

    Bugün tek örnek Şükran Ünlü: eğitim hemşiresi olduğu için izni Cumartesi ya
    da Pazar olmak zorunda (Baran, 29.09) — hangisi olduğunu solver seçer.
    Kural şu: pencerenin DIŞINDAKİ serbest günlerin hepsinde çalışılır.

    TAM HAFTA ŞARTI YOK — C-023'ten farkı bu. "Haftada tam 1 izin" yarım haftada
    anlamsızdır ama "hafta içi izin yapma" her gün için geçerlidir: ayın son
    haftası Cumartesi'de bitiyorsa izin yine Cumartesi'ye düşmeli.

    GÜVENLİK: bir haftada pencereye uyan hiç serbest gün yoksa kısıt konmaz.
    Yoksa C-016 (haftada en az 1 boş gün) ile çelişir ve model çözümsüz olurdu —
    örneğin dönem Çarşamba bitiyorsa o yarım haftada hiç hafta sonu yoktur.
    """
    haftalar: dict[date, list[date]] = {}
    for g in v.gunler:
        pzt = g - timedelta(days=g.weekday())
        haftalar.setdefault(pzt, []).append(g)

    for p in kisiler:
        if not p.off_olabilir_gunler:
            continue
        for gunler in haftalar.values():
            pencere_gunu_var = any(
                g.isoweekday() in p.off_olabilir_gunler and _serbest_gun_mu(p, g, engelli)
                for g in gunler
            )
            if not pencere_gunu_var:
                continue
            for g in gunler:
                if g.isoweekday() in p.off_olabilir_gunler or g not in donem:
                    continue                                # işlenmiş gün değiştirilemez
                if _serbest_gun_mu(p, g, engelli):
                    model.add(calisiyor(p.id, g) == 1)


# ---------------------------------------------------------------------------
# Zorunlu / esnek düğmesi — TEK yerde
# ---------------------------------------------------------------------------


class _KuralUygulayici:
    """Bir kuralın E-03'teki zorunlu/esnek ayarını modele uygular.

    NEDEN: kurallar tek tek elle yazılıyordu. Katı kurallar (C-002, C-014 …)
    `model.add` ile her zaman katıydı — E-03'te "esnek" yapmak hiçbir şey
    değiştirmiyordu. Esnek kurallar ise yalnız ağırlıkla kuruluyordu; "zorunlu"
    yapılınca ağırlık boşalıyor ve kural SESSİZCE devre dışı kalıyordu
    (30.09 ölçümü: C-025 zorunlu → tek tip hafta 3'ten 4'e çıktı).

    Artık her kural buradan geçer:
      is_hard            → kısıt (acil=True ise ACIL_CEZA'lı son çare gevşemesiyle)
      esnek              → ihlal başına kural ağırlığı × ölçek ceza
    Tamamen SABİT bir ifade (geçmiş, işlenmiş gün) kısıt yazılmadan atlanır:
    değiştirilemez, kısıt yazmak yalnız modeli çözümsüz yapabilir.
    """

    def __init__(self, model: cp_model.CpModel) -> None:
        self.model = model
        self.cezalar: list[tuple[int, object]] = []
        self.acil_gevsemeler: list[tuple[str, object]] = []
        self._sayac = 0

    def _gevseme(self, k, ust: int, olcek: int, acil: bool):
        self._sayac += 1
        s = self.model.new_int_var(0, max(1, int(ust)), f"gevseme_{k.kod}_{self._sayac}")
        if k.hard_mi:
            self.cezalar.append((ACIL_CEZA, s))
            self.acil_gevsemeler.append((k.katalog_kodu or k.kod, s))
        else:
            self.cezalar.append((int(k.agirlik or 1) * olcek, s))
        return s

    def _uygula(self, k, ifade, yon: str, sinir: int, olcek: int, ust: int, acil: bool) -> None:
        if isinstance(ifade, int):
            return
        if k.hard_mi and not acil:
            if yon == "<=":
                self.model.add(ifade <= sinir)
            elif yon == ">=":
                self.model.add(ifade >= sinir)
            else:
                self.model.add(ifade == sinir)
            return
        if yon == "<=":
            self.model.add(ifade - self._gevseme(k, ust, olcek, acil) <= sinir)
        elif yon == ">=":
            self.model.add(ifade + self._gevseme(k, ust, olcek, acil) >= sinir)
        else:
            self.model.add(ifade + self._gevseme(k, ust, olcek, acil)
                           - self._gevseme(k, ust, olcek, acil) == sinir)

    def en_fazla(self, k, ifade, sinir, *, olcek: int = YB_DK, ust: int = 31,
                 acil: bool = False) -> None:
        self._uygula(k, ifade, "<=", sinir, olcek, ust, acil)

    def en_az(self, k, ifade, sinir, *, olcek: int = YB_DK, ust: int = 31,
              acil: bool = False) -> None:
        self._uygula(k, ifade, ">=", sinir, olcek, ust, acil)

    def esit(self, k, ifade, sinir, *, olcek: int = YB_DK, ust: int = 31,
             acil: bool = False) -> None:
        self._uygula(k, ifade, "==", sinir, olcek, ust, acil)


# ---------------------------------------------------------------------------
# Çalışma süresi kuralları (seeds/034)
# ---------------------------------------------------------------------------


@dataclass
class _HaftaBaglami:
    """Haftalık kuralların ortak girdisi: hangi haftalar, kimler, hangi günler sabit.

    HAFTA = Pzt–Paz takvim haftası. BİLİNEN gün = dönem içi ya da geçmiş
    penceresinde YAYINLANMIŞ bir çizelgenin kapsadığı gün. Ay başındaki yarım hafta geçmişle (yayınlanmış önceki çizelge)
    tamamlanır; ay sonundaki yarım haftada kurallar bilinen gün sayısıyla
    orantılanır. Tamamen işlenmiş hafta atlanır — değiştirilecek gün yok.
    """

    v: SolverVerisi
    x: dict
    tum_gunler: list
    donem: set
    yok: set          # izin / rapor (kişi, gün)
    bos: set          # KESIN boş gün isteği (kişi, gün)
    calisiyor: object
    gece: object
    gunduz: object
    net: object
    brut: object
    model: object = None

    def __post_init__(self) -> None:
        self.secenek: dict[tuple[int, date], list[str]] = defaultdict(list)
        for (p_id, g, kod) in self.x:
            self.secenek[p_id, g].append(kod)
        self.sure = {vd.kod: vd.sure_dk for vd in self.v.vardiyalar}

    def haftalar(self) -> list[list[date]]:
        bilinen = set(self.v.gunler) | self.v.gecmis_bilinen_gunler
        sonuc: dict[date, list[date]] = {}
        for g in self.v.gunler:
            pzt = g - timedelta(days=g.weekday())
            if pzt not in sonuc:
                sonuc[pzt] = [pzt + timedelta(days=i) for i in range(7)
                              if (pzt + timedelta(days=i)) in bilinen]
        return [gunler for gunler in sonuc.values()
                if len(gunler) >= C016_ASGARI_BILINEN_GUN
                and any(g in self.donem for g in gunler)]

    def kisiler(self, v: SolverVerisi):
        """Haftalık kurallara girenler. Sabit programlı kişinin haftası veridir
        (C-008); oryantasyondaki eşini izler (C-020) — ikisi de kendi haftasını
        seçemez."""
        return [p for p in v.personel if not p.sabit_programli and not p.oryantasyonda]

    def sozlesmeli(self, p, gunler: list[date]) -> bool:
        """Haftanın dönem içindeki her gününde sözleşmesi var mı (ay içinde
        başlayan / ayrılan personelin yarım haftası kurala girmez)."""
        return all(g in p.calisabilir_gunler for g in gunler if g in self.v.gunler)

    def bilinmeyen(self, gunler: list[date]) -> tuple[int, int]:
        """(önce, sonra): haftanın dönem ÖNCESİNDE ve SONRASINDA bilinmeyen gün sayısı."""
        pzt = gunler[0] - timedelta(days=gunler[0].weekday())
        hafta = [pzt + timedelta(days=i) for i in range(7)]
        sonra = sum(1 for g in hafta if g > self.v.gunler[-1])
        return 7 - len(gunler) - sonra, sonra

    def ertesi_zorunlu_bos(self, p_id: int):
        """Dönemin son iki günü gece ise ertesi gün (gelecek ayın ilk günü) C-014
        gereği ZORUNLU boştur. 0/1 ifade: ay sonu yarım haftasında gelecek günleri
        'çalışılabilir' sayarken bu gün düşülür. Aksi halde ay 2 geceyle bitip
        gelecek ayın ilk haftası 45 saate tamamlanamıyordu (Kasım ölçümü, 30.09)."""
        c14 = self.v.kural("C-014")
        n = int(c14.parametreler["rest_trigger_nights"]) if c14 else 0
        if n <= 0:
            return 0
        son = [self.v.gunler[-1] - timedelta(days=i) for i in range(n)]
        geceler = sum(self.gece(p_id, g) for g in son)
        if isinstance(geceler, int):
            return int(geceler >= n)
        b = self.model.new_bool_var(f"ertesi_bos_{p_id}")
        self.model.add(b >= geceler - (n - 1))
        return b

    def tavan(self, p_id: int, gunler: list[date], ifade_fn, deger_fn) -> int:
        """İfadenin ulaşabileceği kaba üst sınır: sabit günlerin değeri + her
        değişkenli günün en büyük seçeneği. Dinlenme kurallarını hesaba katmaz;
        yalnız AÇIKÇA imkânsız haftayı (ör. 3 kesin izin) ayıklamak için."""
        toplam = 0
        for g in gunler:
            e = ifade_fn(p_id, g)
            if isinstance(e, int):
                toplam += e
            elif self.secenek.get((p_id, g)):
                toplam += max(deger_fn(kod) for kod in self.secenek[p_id, g])
        return toplam


def _karma_hafta(kural, v: SolverVerisi, h: _HaftaBaglami) -> None:
    """C-025: gündüz+gece personelin her haftasında en az 1 gündüz ve 1 gece.

    Tek tip hafta dengesizlik üretiyordu: gece 11 saat olduğu için tam gece
    haftası az vardiyada doluyor, geriye 3-4 boş gün kalıyor; aynı hafta başka
    birine tamamen gündüz düşüyor. İzin/raporlu günü olan hafta muaf.
    """
    k = v.kural("C-025")
    if k is None:
        return
    for gunler in h.haftalar():
        for p in h.kisiler(v):
            if p.uygunluk != "gunduz_gece" or not h.sozlesmeli(p, gunler):
                continue
            if any((p.id, g) in h.yok for g in gunler):
                continue
            kural.en_az(k, sum(h.gunduz(p.id, g) for g in gunler), 1, acil=True)
            kural.en_az(k, sum(h.gece(p.id, g) for g in gunler), 1, acil=True)


def _haftalik_yasal_saat(kural, v: SolverVerisi, h: _HaftaBaglami) -> None:
    """C-026: haftalık NET çalışma en az 45 saat (yasal).

    İzin/rapor günü 7,5 saat sayılır.
    AY SONU yarım haftası ORANTILANMAZ: tam 45 saat istenir, dönem sonrasındaki
    her gün gelecek ay en az bir gündüz (8 sa 10 dk) katabilir sayılır — ay 2
    geceyle bitiyorsa ertesi gün C-014 gereği boş olduğundan o gün sayılmaz.
    Orantı (45 × 6/7) ayı "yeterli" bırakıp gelecek ayın ilk haftasını
    imkânsız kılıyordu.
    AY BAŞI yarım haftası (önceki ay yayınlanmamışsa) bilinen günlerle orantılıdır:
    geçmiş değiştirilemez.
    Kesin izin istekleri haftayı açıkça imkânsız kılıyorsa (4 gün × 11 sa = 44)
    kural o hafta kurulmaz; kontrolcü bunu uyarı olarak gösterir.
    """
    k = v.kural("C-026")
    if k is None:
        return
    hedef_dk = int(Decimal(k.parametreler["weekly_min_net_hours"]) * 60)
    kredi_dk = int(Decimal(k.parametreler.get("absence_daily_credit_hours", 0)) * 60)
    gun_dk = min((vd.sure_dk for vd in v.vardiyalar if vd.sadece_rol is None), default=0)
    for gunler in h.haftalar():
        once, sonra = h.bilinmeyen(gunler)
        for p in h.kisiler(v):
            if not h.sozlesmeli(p, gunler):
                continue
            izinli = sum(1 for g in gunler if (p.id, g) in h.yok)
            gerek = hedef_dk * (7 - once) // 7 - izinli * kredi_dk - sonra * gun_dk
            if gerek <= 0:
                continue
            if h.tavan(p.id, gunler, h.net, lambda kod: h.sure[kod]) < gerek:
                continue
            ifade = sum(h.net(p.id, g) for g in gunler)
            if sonra:
                ifade = ifade - gun_dk * h.ertesi_zorunlu_bos(p.id)
            kural.en_az(k, ifade, gerek, olcek=1, ust=gerek + gun_dk, acil=True)


def _haftalik_calisma_gunu(kural, v: SolverVerisi, h: _HaftaBaglami) -> None:
    """C-028: haftada en az 5 gün çalışma, en fazla 2 gün izin.

    İzin/rapor ve kesin izin isteği günleri sayıma girmez (izin sayılmaz, çalışma
    beklenmez). 2 gün ÜST ÜSTE izin serbesttir — sınır haftanın TOPLAMIdır.
    Ay başı yarım haftasında (önceki ay yayınlanmamış) bilinmeyen günler
    çalışılmış varsayılır. Ay SONU yarım haftasında gelecek günler çalışılabilir
    sayılır, ay 2 geceyle bitiyorsa ertesi gün hariç (bkz. C-026).
    """
    k = v.kural("C-028")
    if k is None:
        return
    en_az_is = int(k.parametreler.get("min_weekly_work_days", 0))
    en_fazla_izin = int(k.parametreler.get("max_weekly_off_days", 7))
    for gunler in h.haftalar():
        once, sonra = h.bilinmeyen(gunler)
        for p in h.kisiler(v):
            if not h.sozlesmeli(p, gunler):
                continue
            serbest = [g for g in gunler if (p.id, g) not in h.yok and (p.id, g) not in h.bos]
            disi = len(gunler) - len(serbest)
            if h.tavan(p.id, serbest, h.calisiyor, lambda _kod: 1) + sonra < en_az_is - disi - once:
                continue
            calisma = sum(h.calisiyor(p.id, g) for g in serbest)
            zorunlu_bos = h.ertesi_zorunlu_bos(p.id) if sonra else 0
            # En fazla izin: bilinen izinler + ay sonunun zorunlu boş günü.
            kural.en_az(k, calisma - zorunlu_bos, len(serbest) - en_fazla_izin, acil=True)
            # En az çalışma: bilinen çalışma + gelecekte çalışılabilir günler.
            kural.en_az(k, calisma - zorunlu_bos, en_az_is - disi - once - sonra, acil=True)


def _fazla_mesai(model, v: SolverVerisi, h: _HaftaBaglami) -> list[tuple[int, object]]:
    """O-001 fazla mesai (en aza indir) + O-010 mesai dengesi (eşit dağıt).

    O-001: haftalık BRÜT 51 saatin üstü fazla mesaidir. BRÜT = molalar dahil
    vardiya süresi (gündüz 9,5 sa, gece 14,5 sa) — maaş hesabı böyle (Edem, 30.09).
    Gündüzcünün 6 günü 57 sa → 6 sa mesai: kaçınılmaz, ceza yalnız fazlasını
    azaltmaya iter. Yarım haftada sınır orantılıdır. Zorunlu yapılırsa haftalık
    brüt sınırın üstüne çıkılmaz (acil gevşemeyle).

    O-010: "oluyorsa eşit dağıtılsın" (Baran, 30.09). Kişinin AYLIK mesaisi =
    Pazar'ı döneme düşen haftaların fazlası (raporla aynı tanım). Kağıttan gelen
    işlenmiş haftanın mesaisi SABİT olarak girer; solver kalan haftalarda telafi
    eder. Sapma gerçek ortalamadan ölçülür (|n·mᵢ − Σm|, bölmesiz) + en çok − en az.
    """
    k = v.kural("O-001")
    if k is None or "weekly_paid_gross_hours" not in k.parametreler:
        return []
    sinir_dk = int(Decimal(k.parametreler["weekly_paid_gross_hours"]) * 60)
    terimler: list[tuple[int, object]] = []
    mesai: dict[tuple[int, date], object] = {}      # (kişi, Pazartesi) → dakika
    for gunler in h.haftalar():
        sinir = sinir_dk * len(gunler) // 7
        pzt = gunler[0] - timedelta(days=gunler[0].weekday())
        for p in h.kisiler(v):
            if not h.sozlesmeli(p, gunler):
                continue
            hafta = sum(h.brut(p.id, g) for g in gunler)
            if isinstance(hafta, int):
                continue
            f = model.new_int_var(0, 7 * 24 * 60, f"mesai_{p.id}_{gunler[0]}")
            model.add(f >= hafta - sinir)
            mesai[p.id, pzt] = f
            if k.hard_mi:
                terimler.append((ACIL_CEZA, f))
            elif k.agirlik:
                terimler.append((int(k.agirlik), f))

    denge = v.kural("O-010")
    if denge is None or (not denge.hard_mi and not denge.agirlik):
        return terimler
    havuz = [p for p in h.kisiler(v) if p.adalete_girer]
    if len(havuz) < 2:
        return terimler
    bilinen = set(v.gunler) | v.gecmis_bilinen_gunler
    pazartesiler = [g - timedelta(days=6) for g in v.gunler if g.isoweekday() == 7]
    aylik: dict[int, object] = {}
    for p in havuz:
        toplam = 0
        for pzt in pazartesiler:
            if (p.id, pzt) in mesai:
                toplam += mesai[p.id, pzt]
                continue
            # Tamamen işlenmiş hafta: mesaisi sabit.
            gunler = [pzt + timedelta(days=i) for i in range(7)
                      if pzt + timedelta(days=i) in bilinen]
            hafta = sum(h.brut(p.id, g) for g in gunler)
            if isinstance(hafta, int):
                toplam += max(0, hafta - sinir_dk * len(gunler) // 7)
        # Ayın dönemden ÖNCEKİ haftaları (hafta hafta üretimde önceki taslaklar).
        toplam += sum(max(0, b - sinir_dk) for b in (v.ay_basi_hafta_brut or {}).get(p.id, ()))
        aylik[p.id] = toplam
    if all(isinstance(m, int) for m in aylik.values()):
        return terimler

    # Denge ÇALIŞMA TİPİ İÇİNDE kurulur: sadece gündüzcünün mesaisi yapısal olarak
    # sabit (her hafta 6 gün × 9,5 = 57 → 6 sa). Tek havuzda gündüz+gece
    # çalışanlar da imkânsız bir 18 saate çekiliyordu (ölçüm 30.09: fark 32,5 → 28).
    ust = 31 * 24 * 60
    gruplar: dict[str, list[int]] = defaultdict(list)
    for p in havuz:
        gruplar[p.uygunluk].append(p.id)
    fark_dk = int(Decimal(denge.parametreler.get("max_monthly_gap_hours", 10)) * 60)
    for tip, kimler in gruplar.items():
        degerler = [aylik[i] for i in kimler]
        if len(kimler) < 2 or all(isinstance(m, int) for m in degerler):
            continue
        en_cok = model.new_int_var(0, ust, f"mesai_encok_{tip}")
        en_az = model.new_int_var(0, ust, f"mesai_enaz_{tip}")
        for m in degerler:
            model.add(en_cok >= m)
            model.add(en_az <= m)
        if denge.hard_mi:
            s = model.new_int_var(0, ust, f"mesai_denge_acil_{tip}")
            model.add(en_cok - en_az - s <= fark_dk)
            terimler.append((ACIL_CEZA, s))
            continue
        w = int(denge.agirlik)
        terimler.append((w, en_cok - en_az))
        n = len(kimler)
        toplam = sum(degerler)
        sapmalar = []
        for p_id in kimler:
            sp = model.new_int_var(0, ust * n, f"mesai_sapma_{p_id}")
            model.add(sp >= n * aylik[p_id] - toplam)
            model.add(sp >= toplam - n * aylik[p_id])
            sapmalar.append(sp)
        terimler.append((max(1, w // n), sum(sapmalar)))
    return terimler


def _gunluk_denge(model, v: SolverVerisi, x: dict, kapsama_sayilan: set[int],
                  sabit_kapsama, donem: set) -> list[tuple[int, object]]:
    """O-009: asgarinin üstündeki fazla kadro günlere eşit dağılsın.

    Aylık 200 saat hedefi ihtiyaçtan fazla vardiya yazdırıyor; fazlanın nereye
    gideceğini söyleyen bir kural yoktu ve solver gündüzleri 5 ile 8 arasında
    rastgele dolduruyordu (30.09 ölçümü, Ekim). Her vardiya türü için
    (en kalabalık gün fazlası − en seyrek gün fazlası) cezalandırılır.
    Zorunlu yapılırsa fark en fazla 1 kişi olur (acil gevşemeyle).
    """
    k = v.kural("O-009")
    if k is None or (not k.hard_mi and not k.agirlik):
        return []
    gunun: dict[tuple[date, str], list] = defaultdict(list)
    for (p_id, g, kod), d in x.items():
        if p_id in kapsama_sayilan:
            gunun[g, kod].append(d)

    fazlalar: dict[str, list] = defaultdict(list)
    for satir in v.ihtiyaclar:
        if satir.slot_kodu != "GENEL":
            continue
        for g in satir.gunler:
            if g not in donem:
                continue
            ekip = sum(gunun.get((g, satir.vardiya_kodu), [])) + sabit_kapsama.get(
                (g, satir.vardiya_kodu), 0)
            if isinstance(ekip, int):
                continue
            fazlalar[satir.vardiya_kodu].append(ekip - satir.min_sayi)

    terimler: list[tuple[int, object]] = []
    # GECE FAZLASI doğrudan cezalı (01.10): gecede asgarinin üstü kadro istenmiyor.
    # Dönemin son gecelerinin ertesi gün dinlenme bedeli bu taslakta görünmediği
    # için solver eksik saatleri oraya yığıyordu (5–11 Ekim: Cmt 7, Paz 8–10 gece).
    gece_kodlari = {vd.kod for vd in v.vardiyalar if vd.gece_mi}
    if not k.hard_mi:
        for kod in gece_kodlari & set(fazlalar):
            for i, d in enumerate(fazlalar[kod]):
                f = model.new_int_var(0, 50, f"gece_fazla_{kod}_{i}")
                model.add(f >= d)
                terimler.append((_sayi(k.agirlik), f))
    for kod, degerler in fazlalar.items():
        if len(degerler) < 2:
            continue
        en_cok = model.new_int_var(-50, 50, f"denge_encok_{kod}")
        en_az = model.new_int_var(-50, 50, f"denge_enaz_{kod}")
        for d in degerler:
            model.add(en_cok >= d)
            model.add(en_az <= d)
        if k.hard_mi:
            s = model.new_int_var(0, 50, f"denge_acil_{kod}")
            model.add(en_cok - en_az - s <= 1)
            terimler.append((ACIL_CEZA, s))
        else:
            terimler.append((_sayi(k.agirlik), en_cok - en_az))
    return terimler



def _oryantasyon_esi(model, v: SolverVerisi, x: dict, takviye: dict,
                     engelli: set) -> list[tuple[int, object]]:
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

    DİNLENEN ORYANTASYON (30.09): gölgeleme (x[oryantasyon] >= x[eş]) artık
    KATI değil, cezalı. Oryantasyondaki kişi dinlenme kuralı yüzünden o gün
    çalışamıyorsa (ör. işlenmiş haftada 4 Ekim gecesi → 5 Ekim gündüz yasak)
    katı eşitlik EŞİNİ de çalışamaz yapıyordu; eşin haftalık izin deseni o günü
    zorunlu kıldığında model çözümsüz kalıyordu. Kural oryantasyondakini eşine
    bağlar, eşi oryantasyondakine değil: eş tek başına çalışabilir, bedeli
    GOLGE_CEZASI. "Eşsiz çalışmaz" yönü (<=) KATI kalır.
    """
    cezalar: list[tuple[int, object]] = []
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
                    continue
                golge = model.new_bool_var(f"golge_{o.id}_{g}_{s.kod}")
                model.add(oryantasyon + golge >= es)
                cezalar.append((_sayi(GOLGE_CEZASI), golge))
                model.add(oryantasyon <= es + (tak if tak is not None else 0))
    return cezalar


def _adalet_ve_saat(model, v: SolverVerisi, x: dict, t: dict,
                    adalet_havuzu: set[int], kural) -> tuple[list[tuple[int, object]], dict]:
    """C-004, C-027, O-002…O-005.

    Ağırlıklar VERİTABANINDAN (constraints.default_weight), kodda gizli çarpan yok.
    BİRİM ÖLÇEĞİ burada: gece ve hafta sonu sayıları adet cinsinden olduğu için
    vardiyanın NET süresiyle çarpılıp dakikaya çevrilir (bir gece 660 dk, ortalama
    vardiya ~575 dk). Böylece "bir gece fazla" ile "11 saat fazla" aynı dilde
    konuşur. Ambulans rozeti bir GÖREVdir, süre değil — ölçek yerine _sayi()
    ile modelin dakika ölçeğine taşınır (bkz. YB_DK).

    Döndürür: (amaç terimleri, çözümden sonra okunacak değişkenler)
    """
    terimler: list[tuple[int, object]] = []
    kisiler = [p for p in v.personel if p.id in adalet_havuzu]
    sure = {vd.kod: vd.sure_dk for vd in v.vardiyalar}
    gece_kodlari = {vd.kod for vd in v.vardiyalar if vd.gece_mi}
    gece_dk = max((vd.sure_dk for vd in v.vardiyalar if vd.gece_mi), default=660)
    vardiya_dk = round(sum(sure.values()) / len(sure))

    def agirlik(katalog: str) -> int:
        kural = v.kural(katalog)
        return int(kural.agirlik) if kural and kural.agirlik else 0

    # ---- Kişi başına toplamlar ----
    kisi_gunleri: dict[int, list] = defaultdict(list)
    for (p_id, g, kod), d in x.items():
        kisi_gunleri[p_id].append((g, kod, d))

    # Dönem içindeki SABİT satırlar (elle yazılmış, kilitli, işlenmiş günler)
    # da kişinin ayına sayılır. Eskiden yalnız değişkenler toplanıyordu: işlenmiş
    # 1–4 Ekim'i çalışan biri 200 saate o günler hiç yokmuş gibi zorlanırdı.
    sabit_dk: Counter[int] = Counter()
    sabit_gece: Counter[int] = Counter()
    sabit_hs: Counter[int] = Counter()
    for sa in v.sabit_atamalar:
        sabit_dk[sa.personel_id] += sa.sure_dk
        sabit_gece[sa.personel_id] += int(sa.gece_mi)
        sabit_hs[sa.personel_id] += int(sa.gun.isoweekday() >= 6)

    saat, gece, hafta_sonu, ambulans = {}, {}, {}, {}
    for p in kisiler:
        kendi = kisi_gunleri[p.id]
        # AY BAŞINDAN İTİBAREN toplam (01.10): hafta hafta üretilen taslak, ayın
        # önceki yayınlanmış günlerini devralır. Aylık taslakta ay başı boştur.
        saat[p.id] = (sum(d * sure[kod] for _g, kod, d in kendi) + sabit_dk[p.id]
                      + v.ay_basi_saatler_dk.get(p.id, 0))
        gece[p.id] = (sum(d for _g, kod, d in kendi if kod in gece_kodlari) + sabit_gece[p.id]
                      + (v.ay_basi_gece or {}).get(p.id, 0))
        hafta_sonu[p.id] = (sum(d for g, _k, d in kendi if g.isoweekday() >= 6)
                            + sabit_hs[p.id] + (v.ay_basi_hafta_sonu or {}).get(p.id, 0))
    for p in kisiler:
        ambulans[p.id] = sum(
            d for (p_id, _g, _v, gorev), d in t.items()
            if p_id == p.id and gorev == "AMBULANS"
        )

    # ---- C-004: aylık en az 200 saat (izin günü başına düşülerek) ----
    izin = Counter(y.personel_id for y in v.yokluklar)
    dusum = v.kural("C-004").parametreler.get("absence_daily_reduction_hours")
    # İzin/rapor günü kredisi 7,5 saat NET (Edem, 29.09) → 450 dakika.
    dusum_dk = int(Decimal(dusum) * 60) if dusum is not None else 0

    # AY İÇİNDE BİTEN TASLAK (hafta hafta üretim): aylık hedef taslağın bittiği
    # güne kadar ORANTILI. 5–11 Ekim taslağı 200 saatin 11/31'ini ister (71 sa,
    # 1–4 Ekim dahil). Eskiden ayın tamamını istiyordu: "200 − (1–4 Ekim)" bir
    # haftaya sığmaz, solver herkesi alabildiğine yazıyor, haftalar 57–60 saate,
    # Pazar gecesi 11 kişiye çıkıyordu (01.10 ölçümü).
    son = v.gunler[-1]
    ay_son_gunu = calendar.monthrange(son.year, son.month)[1]
    if v.gunler[0].month == son.month and son.day < ay_son_gunu:
        oran = (son.day, ay_son_gunu)
    else:
        oran = (1, 1)

    hedef_saat, eksik_saat = {}, {}
    ulasamayanlar = []
    for p in kisiler:
        ay_hedefi = max(0, p.hedef_saat_dk - izin[p.id] * dusum_dk)
        if oran == (1, 1):
            hedef = ay_hedefi
        else:
            # AÇIK KALAN GÜNLERE BÖLÜNÜR (Baran, 01.10): ayın önceki günlerinde
            # az çalışan (Engin: 1–4 Ekim'de 16 sa) açığını TEK haftada değil,
            # ayın kalan günlerine eşit dağıtarak kapatır. 5–11 Ekim kalan 27
            # günün 7'si → açığın 7/27'si bu hafta. Eskiden açığın tamamı ilk
            # haftaya biniyor, Engin 60 saate çıkıyordu.
            # Bilinmeyen (yayınlanmamış) ara günler de kendi payını taşır: açık
            # İLK BİLİNMEYEN günden ay sonuna bölünür. 5–11 yayınlanmadan 12–18
            # çözülürse açığın 7/27'si istenir, 7/20'si değil (01.10).
            onceki = v.ay_basi_saatler_dk.get(p.id, 0)
            bilinmeyen = (v.gunler[0] - date(son.year, son.month, 1)).days - v.ay_basi_bilinen_gun
            kalan_gun = ((date(son.year, son.month, ay_son_gunu) - v.gunler[0]).days + 1
                         + max(0, bilinmeyen))
            hedef = onceki + max(0, ay_hedefi - onceki) * len(v.gunler) // kalan_gun
        hedef_saat[p.id] = hedef
        e = model.new_int_var(0, hedef, f"saat_eksik_{p.id}")
        model.add(saat[p.id] + e >= hedef)
        eksik_saat[p.id] = e

        # HEDEFE TAM ULAŞMA — açığın BÜYÜKLÜĞÜNDEN bağımsız, sabit ek ceza.
        # Vardiyalar 490 ve 660 dakikalık parçalar: 10 gece + 11 gündüz = 11.990 dk
        # = 199,83 saat, hedefin 10 dakika altı. Yalnız orantılı ceza varken solver
        # o 10 dakikayı kapatmak yerine açık bırakmayı tercih ediyordu; bir vardiya
        # daha eklemek 208 saate fırlatıyor. Sabit ceza son adımı kârlı kılıyor.
        ulasti = model.new_bool_var(f"hedefe_ulasti_{p.id}")
        model.add(e == 0).only_enforce_if(ulasti)
        model.add(e >= 1).only_enforce_if(ulasti.Not())
        ulasamayanlar.append(ulasti.Not())
    terimler.append((SAAT_EKSIGI_CEZASI, sum(eksik_saat.values())))

    tam_hedef = v.kural("C-004").parametreler.get("exact_target_penalty")
    # Yalnız AY SONUNA giden taslakta: "hedefin 10 dk altı" sorunu ayın toplamına
    # ait. Ay ortasında biten taslakta (hafta hafta) orantılı hedefi dakikası
    # dakikasına tutturmak anlamsız; bonus solver'ı dönemin son gecesine fazla
    # kişi yazmaya itiyordu (01.10: 5–11 Ekim taslağında Pazar gecesi 10 kişi).
    if tam_hedef and oran == (1, 1):
        # Kişi SAYAR (adet), zaman taşımaz → model ölçeğine _sayi() ile taşınır.
        terimler.append((_sayi(int(tam_hedef)), sum(ulasamayanlar)))

    # ---- C-027: aylık YASAL asgari (net 180 sa) ----
    # C-004'ten farkı: 200 bir HEDEF (cezalı), 180 yasal ALT SINIR (katı).
    # Yalnız tam takvim ayı olan taslakta anlamlı; izin/rapor günü C-004'ün
    # düşümüyle aynı kredi (7,5 sa) sayılır.
    yasal = v.kural("C-027")
    bas, son = v.gunler[0], v.gunler[-1]
    tam_ay = bas.day == 1 and (son + timedelta(days=1)).day == 1
    if yasal and tam_ay:
        asgari_dk = int(Decimal(yasal.parametreler["monthly_legal_min_net_hours"]) * 60)
        for p in kisiler:
            gerek = max(0, asgari_dk - izin[p.id] * dusum_dk)
            kural.en_az(yasal, saat[p.id], gerek,
                        olcek=1, ust=gerek, acil=True)

    # ---- O-002…O-005: adalet ----
    # Her biri İKİ parça: uçlar arası fark + herkesin hedefe uzaklığı. Sadece
    # max−min cezalandırmak ortadaki kişileri görmez — iki uç düzelir, geri kalan
    # çarpık kalır.
    gece_havuzu = [p for p in kisiler if p.uygunluk != "sadece_gunduz"]
    amb_havuzu = [p for p in kisiler if "AMBULANS" in p.yetkinlikler]
    beklenen = _beklenen_yukler(v)
    hedefler: dict[str, int] = {}

    for katalog, ad, deger, havuz, olcek, ust in (
        # (katalog, ad, değer, havuz, ölçek, üst sınır)
        # ölçek: değeri modelin DAKİKA diline çeviren çarpan. Saat zaten dakika →
        # 1. Gece/hafta sonu adet → net vardiya süresiyle çarpılır. Ambulans
        # adet ve süreyle ilgisi yok → _sayi() ölçeği (YB_DK).
        ("O-002", "saat",       saat,       kisiler,     1,           40_000),
        ("O-003", "gece",       gece,       gece_havuzu, gece_dk,         40),
        ("O-004", "hafta_sonu", hafta_sonu, kisiler,     vardiya_dk,      40),
        ("O-005", "ambulans",   ambulans,   amb_havuzu,  YB_DK,           80),
    ):
        w = agirlik(katalog)
        if not w or len(havuz) < 2:
            continue
        hedef_ort = round(beklenen[ad] / len(havuz))

        # ADALET HEDEFİ ZORUNLU ASGARİNİN ALTINA DÜŞEMEZ.
        #
        # Beklenen yük ihtiyaç ŞABLONUNDAN geliyor. Şablon 19 kişilik havuza
        # kişi başı 156 saat veriyor, ama C-004 herkesten 200 saat İSTİYOR.
        # Hedef 156'da bırakılırsa adalet kuralı saat kuralına karşı çalışır:
        # herkes zorunlu olarak 44 saat "sapmış" sayılır ve fazladan tek bir
        # gündüz vardiyası 490 dk × 2200 = 1.078.000 ceza yazar. Ölçüldü
        # (Ekim 2026): solver 10 kişiyi hedefin 10 DAKİKA altında bırakmayı,
        # bir vardiya daha eklemeye tercih ediyordu.
        #
        # Adalet "herkes birbirine yakın olsun" demektir; kimsenin ulaşamayacağı
        # bir ortalamaya yaklaşmak değil. Hedefi zorunlu asgariye çekiyoruz.
        if ad == "saat" and hedef_saat:
            zorunlu_ort = round(sum(hedef_saat[p.id] for p in havuz) / len(havuz))
            hedef_ort = max(hedef_ort, zorunlu_ort)
        hedefler[ad] = hedef_ort
        degerler = [deger[p.id] for p in havuz]

        if ad == "saat" and hedef_saat:
            # SAAT ADALETİ HERKESİN KENDİ ROTASINA GÖRE (01.10): ölçülen, kişinin
            # ay başından toplam saatinin kendi dönem hedefinden sapması. Ham
            # toplamları eşitlemek (ortalamadan sapma) ayın başında geride kalanı
            # TEK haftada yetiştirmeye zorluyordu; hedef açığı kalan günlere
            # bölündüğü için rotada olmak = adil.
            farklar = [deger[p.id] - hedef_saat[p.id] for p in havuz]
            if UC_FARKI_CEZALANDIR:
                en_cok = model.new_int_var(-ust, ust, "encok_saat")
                en_az = model.new_int_var(-ust, ust, "enaz_saat")
                model.add_max_equality(en_cok, farklar)
                model.add_min_equality(en_az, farklar)
                terimler.append((w * olcek, en_cok - en_az))
            sapmalar = []
            for p, f in zip(havuz, farklar):
                sp = model.new_int_var(0, ust, f"sapma_saat_{p.id}")
                model.add(sp >= f)
                model.add(sp >= -f)
                sapmalar.append(sp)
            terimler.append((w * olcek, sum(sapmalar)))
            continue

        if UC_FARKI_CEZALANDIR:
            en_cok = model.new_int_var(0, ust, f"encok_{ad}")
            en_az = model.new_int_var(0, ust, f"enaz_{ad}")
            model.add_max_equality(en_cok, degerler)
            model.add_min_equality(en_az, degerler)
            terimler.append((w * olcek, en_cok - en_az))

        sapmalar = []
        if ad in ("gece", "hafta_sonu"):
            # SAPMA ŞABLON HEDEFİNDEN DEĞİL GERÇEK ORTALAMADAN ölçülür.
            # Şablon hedefi asgari kadrodan geliyor; 200 saat hedefinin yazdırdığı
            # fazla vardiyaları görmüyor. Herkes "hedefin üstünde" sayılınca solver
            # fazlayı hafta içine yığıyordu (30.09 ölçümü: hafta sonu gündüz 5,
            # hafta içi 8). Değerler ay başından toplam olduğu için (hafta hafta
            # üretim) şablon hedefi zaten karşılaştırılamaz. 200 saati C-004 korur.
            # Bölme yapmadan ortalamadan sapma: |n·xᵢ − Σx|, ağırlık /n.
            n = len(havuz)
            toplam = sum(degerler)
            for p in havuz:
                sp = model.new_int_var(0, ust * n, f"sapma_{ad}_{p.id}")
                model.add(sp >= n * deger[p.id] - toplam)
                model.add(sp >= toplam - n * deger[p.id])
                sapmalar.append(sp)
            terimler.append((max(1, w * olcek // n), sum(sapmalar)))
            continue
        for p in havuz:
            sp = model.new_int_var(0, ust, f"sapma_{ad}_{p.id}")
            model.add(sp >= deger[p.id] - hedef_ort)
            model.add(sp >= hedef_ort - deger[p.id])
            sapmalar.append(sp)
        terimler.append((w * olcek, sum(sapmalar)))

    olcumler = {"hedefler": hedefler, "hedef_saat": hedef_saat, "eksik_saat": eksik_saat}
    return terimler, olcumler


def _tercihler(model, v: SolverVerisi, x: dict, t: dict,
               kapsama_sayilan: set[int], olcumler: dict) -> list[tuple[int, object]]:
    """O-006 karşılanamayan istek · O-007 triyajda hasta iletişimi · O-008 ambulans alan dağılımı.

    Üçü de YUMUŞAK: ihlal çizelgeyi engellemez, ceza puanı yazar. Ağırlıklar
    veritabanından (seeds/016).

    Üçü de ADET sayar (kaç istek karşılanmadı, kaç rozet yanlış kişide), zaman
    taşımaz → _sayi() ile modelin dakika ölçeğine taşınır (bkz. YB_DK).
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
            terimler.append((_sayi(kural.agirlik), b))
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
            terimler.append((_sayi(kural.agirlik), sum(iletisimsiz)))

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
            terimler.append((_sayi(kural.agirlik), sum(cezalar)))
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
            yuk["saat"] += satir.min_sayi * len(satir.gunler) * vardiya.sure_dk
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


def _sabit_desen_plani(v: SolverVerisi, engelli: set[tuple[int, date]]) -> list[tuple[int, date, str]]:
    """Haftanın tamamı bağlı olan kişilerin planı: seçim değil, sabit girdi.

    Bugün yalnız sorumlu hemşire böyle (C-008: Pzt–Cum gündüz, Cmt kısa vardiya,
    Pazar izin). Desen artık staff_weekly_patterns'ta veri — gün, vardiya ve kişi
    adı kodda geçmez. İzinli/raporlu gün (engelli) plana girmez.
    """
    mevcut = {s.kod for s in v.vardiyalar}
    plan = []
    for p in v.personel:
        if not p.sabit_programli:
            continue
        for g in v.gunler:
            if (p.id, g) in engelli or g not in p.calisabilir_gunler:
                continue
            kod = p.sabit_vardiyalar.get(g.isoweekday())
            if kod and kod in mevcut:
                plan.append((p.id, g, kod))
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


def _islenmis_gunleri_esitle(draft_id: int) -> int:
    """İşlenmiş günleri yayınlanmış çizelgeden taslağa KİLİTLİ kopyalar.

    "Yayınlanmış = işlenmiş" (Baran, 30.09). Kağıt hafta 28.09–04.10 yayındayken
    Ekim taslağı 1–4 Ekim'i yeniden planlamaz: o günlerin satırları taslağa
    source='referans', is_locked=TRUE olarak yazılır (rozetleriyle). Solver o
    günlerde değişken açmaz; haftalık kurallar bu satırları sabit değer olarak
    görür ve haftanın kalanını ona göre kurar.

    Her koşuda yeniden yazılır: yayındaki hafta sonradan düzeltilirse taslak
    kendiliğinden güncel kalır. Taslak yayınlanınca eski yayın arşive gider ama
    bu günler taslağın içinde olduğu için hiçbir gün kaybolmaz.
    """
    with psycopg.connect(get_settings().database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TEMP TABLE _islenmis ON COMMIT DROP AS
                SELECT a.id AS kaynak_id, a.staff_id, a.shift_type_id, a.work_date
                FROM schedule_drafts d
                JOIN schedule_drafts y ON y.unit_id = d.unit_id AND y.id <> d.id
                                      AND y.status = 'yayinlandi' AND y.period && d.period
                                      AND lower(y.period) < lower(d.period)
                JOIN assignments a     ON a.draft_id = y.id
                                      AND y.period @> a.work_date
                                      AND d.period @> a.work_date
                WHERE d.id = %(d)s
                """,
                {"d": draft_id},
            )
            cur.execute(
                """
                DELETE FROM assignments a
                USING schedule_drafts d, schedule_drafts y
                WHERE a.draft_id = %(d)s AND d.id = a.draft_id
                  AND y.unit_id = d.unit_id AND y.id <> d.id AND y.status = 'yayinlandi'
                  AND lower(y.period) < lower(d.period)
                  AND y.period @> a.work_date AND d.period @> a.work_date
                """,
                {"d": draft_id},
            )
            cur.execute(
                """
                INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date,
                                         source, is_locked)
                SELECT %(d)s, staff_id, shift_type_id, work_date, 'referans', TRUE
                FROM _islenmis
                """,
                {"d": draft_id},
            )
            adet = cur.rowcount
            cur.execute(
                """
                INSERT INTO assignment_tasks (assignment_id, competency_id)
                SELECT y.id, t.competency_id
                FROM _islenmis i
                JOIN assignments y      ON y.draft_id = %(d)s AND y.staff_id = i.staff_id
                                       AND y.work_date = i.work_date
                JOIN assignment_tasks t ON t.assignment_id = i.kaynak_id
                ON CONFLICT DO NOTHING
                """,
                {"d": draft_id},
            )
        conn.commit()
    return adet


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
        _eksik_gecmis_uyarisi(v, run_id)
        + aciklama.eksik_aciklamalari(v, cozum, run_id)
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


def _eksik_gecmis_uyarisi(v: SolverVerisi, run_id: int) -> list[tuple]:
    """Dönemden önceki günler yayınlanmamışsa uyarı (01.10).

    Hafta hafta üretimde önceki hafta yayınlanmadan sonraki çözülürse o günler
    BİLİNMİYOR: dinlenme kuralları (gece → gündüz, 2 gece sonrası boş) dönemin
    ilk günlerini kısıtlayamaz ve aylık devir eksik kalır. Ölçüm: 5–11 Ekim
    yayınlanmadan 12–18 çözülünce Pazartesi gündüz 11 kişi (yayınlıyken 6).
    Tahminle doldurmuyoruz; kullanıcıya söylüyoruz.
    """
    bas = v.gunler[0]
    onceki_hafta = {bas - timedelta(days=i) for i in range(1, 8)}
    eksik = sorted(onceki_hafta - set(v.gecmis_bilinen_gunler))
    if not eksik:
        return []
    return [(
        run_id, "uyari", None, None,
        f"Dönemden önceki {len(eksik)} gün ({eksik[0]:%d.%m}–{eksik[-1]:%d.%m}) yayınlanmamış: "
        "dinlenme kuralları dönemin ilk günlerine uygulanamadı, aylık devir eksik.",
        "Önceki haftayı/ayı yayınlayıp bu taslağı yeniden çözün.",
    )]


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
        "islenmis_gunler": [g.isoformat() for g in sorted(v.islenmis_gunler)],
        "kapsanan_kurallar": ["C-002", "C-004", "C-005", "C-006", "C-007",
                              "C-008", "C-009", "C-010", "C-011", "C-014", "C-016",
                              "C-017", "C-019", "C-020", "C-021", "C-023", "C-024", "C-025",
                              "C-026", "C-027", "C-028",
                              "O-001", "O-002", "O-003", "O-004", "O-005", "O-009", "O-010",
                              "all_crew_triage_or_observation",
                              "count_authority_required"],
        "kapsam_disi": ["C-013"],
        "agirliklar": {"eksik_cezasi_yedek": EKSIK_CEZASI_YEDEK,
                       "saat_eksigi_cezasi": SAAT_EKSIGI_CEZASI,
                       "atama_maliyeti": ATAMA_MALIYETI, "rozet_maliyeti": ROZET_MALIYETI},
        "adalet_hedefleri": cozum.hedefler,
        "cozucu": {"tohum": RASTGELE_TOHUM, "isci": get_settings().solver_workers},
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
