# Denetim — canlıya almadan önce

> 28 Eylül 2026 · Solver Adım 1-6 tamamlandıktan sonra, Adım 7 (canlıya alma)
> öncesi yapılan inceleme. **Bu belge yalnızca rapordur; hiçbir şey düzeltilmedi.**
> Öncelik listesi en altta.

---

## A) GÜVENLİK

### A1. Gizli bilgiler

| Kontrol | Sonuç |
|---|---|
| `.env` dosyaları commit edilmiş mi | **Hayır.** `.gitignore` `.env`, `.env.local`, `.env.*.local` kapsıyor. `git ls-files` yalnız `api/.env.example` ve `web/.env.example` döndürüyor. |
| Git geçmişinde şifre / bağlantı dizesi / token | **Yok.** Tüm geçmiş tarandı; tek eşleşme `.env.example`'daki yer tutucu satır (`KULLANICI:PAROLA@ep-xxx-pooler…`). |
| Repo görünürlüğü | **PRIVATE** (`barkobt/nobet_zekasi`). |
| Loglarda sızıntı | `rebuild.sh` ve `migrate.sh` bağlantı dizesini `sed` ile maskeleyip yalnız host + veritabanı adını basıyor. API tarafında bağlantı dizesi loglanmıyor. |

**Tek uyarı:** `DEMO_PASSWORD` ve `DEMO_API_TOKEN` üç ayrı yerde elle tutuluyor
(yerel `.env`, Railway, Vercel). Rotasyon gerekirse üçünü birden değiştirmek
gerekir; unutulan biri 401 üretir. Yazılı bir rotasyon adımı yok.

### A2. Veritabanı yetkisi

**Doğrulanamadı — Neon panelinden kontrol edilmeli.** `docs/deploy.md`'ye göre
Railway'e girilen `DATABASE_URL` Neon'un verdiği hazır dizedir; Neon varsayılanı
`neondb_owner`, yani **veritabanı sahibi**. Uygulama çalışma anında `CREATE TABLE`,
`DROP TABLE`, `ALTER` yetkisine ihtiyaç duymuyor — yalnız `SELECT/INSERT/UPDATE/DELETE`.

**Öneri: ayrı bir uygulama kullanıcısı.**

```sql
-- Neon SQL Editor'de, sahip hesapla bir kez:
CREATE ROLE nobet_app LOGIN PASSWORD '<güçlü-parola>';
GRANT CONNECT ON DATABASE neondb TO nobet_app;
GRANT USAGE ON SCHEMA public TO nobet_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nobet_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nobet_app;
-- Sonradan eklenen tablolar için varsayılan:
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nobet_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO nobet_app;
```

Railway `DATABASE_URL`'i `nobet_app` ile kurulur; migration'lar sahip hesapla
(`DATABASE_URL_DIRECT`) yerelden koşturulmaya devam eder. Böylece canlı uygulama
kazayla da olsa şema değiştiremez.

### A3. SQL enjeksiyonu

**Temiz.** `api/app` ve `api/solver` altında SQL'i string birleştirmeyle ya da
f-string ile kuran **tek bir yer yok**; tüm sorgular psycopg parametreleriyle
(`%s`) çalışıyor. Daha önce `data.py`'de kolon adı için bir f-string vardı
(`_istekler`), migration 014 uygulanınca kaldırıldı.

Tek dinamik parça `api/app/repositories/setup.py:112` — `UPDATE constraints SET
{parcalar} WHERE id = %s`. `parcalar` kullanıcı girdisinden değil, sabit bir
alan adı listesinden üretiliyor; değerler yine parametre. Enjeksiyon riski yok
ama kalıp kırılgan: yeni bir alan eklenirken listeye kullanıcı girdisi karışırsa
açık oluşur.

### A4. API erişimi

> **Canlıda doğrulandı (28.09).** Railway API'ye token'sız ve yanlış token'la
> doğrudan istek atıldı: `/api/staff`, `/api/drafts` → **401**. `/api/health` →
> 200 (beklenen). Koruma çalışıyor. Vercel'de token boşken sitenin "çalışıyor"
> görünmesinin sebebi, korumasız tek sayfanın giriş ekranı olması: `/` ve
> `/personel` oturumsuz **307 → /giris** veriyor, veri isteyen hiçbir sayfa
> açılmıyor. `/openapi.json` ve `/docs` hâlâ 200 — `ENVIRONMENT=production`
> Railway'e girilince kapanacak.


`api/app/main.py:34-49` — tüm istekler `x-demo-token` başlığıyla doğrulanıyor.
Token web'in **sunucu tarafı** proxy'sinde kalıyor (`web/src/app/api/[...path]/route.ts`),
tarayıcıya hiç inmiyor.

**Korumasız uçlar (bilerek):**

| Uç | Neden açık | Risk |
|---|---|---|
| `/api/health` | Railway sağlık kontrolü | Düşük — tablo/view sayısı ve aktif personel **sayısı** sızıyor, ad sızmıyor |
| `/openapi.json` | `openapi-typescript` tip üretimi | **Orta** — tüm API yüzeyi, şema adları, alan adları herkese açık |
| `/docs`, `/redoc` | Swagger arayüzü | **Orta** — aynı bilgi, üstelik tarayıcıdan denenebilir uçlarla |

`/docs` ve `/redoc` canlıda kapatılabilir (`FastAPI(docs_url=None, redoc_url=None)`);
`/openapi.json` tip üretimi için gerekli ama o da yerelden üretilebilir.

**`DEMO_API_TOKEN` Railway'de boş bırakılırsa doğrulama tamamen kapanır** ve API
internete açık hale gelir. `docs/deploy.md` bunu "Baran — dashboard" olarak
işaretlemiş; **canlıya almadan önce dolu olduğu doğrulanmalı.**

### A5. Şifre ekranı

`web/src/proxy.ts` — tek ortak şifre → `clinorq_demo` çerezi. Çerez bayrakları doğru:
`httpOnly`, `sameSite: lax`, `secure` (üretimde), `maxAge` 12 saat.

**İki zayıflık:**

1. Çerez değeri `SHA-256("clinorq:" + parola)` — **sunucuya ait
   ayrı bir gizli anahtar yok**. Ön ek bilindiği için, çerez bir kez sızarsa zayıf
   bir parola çevrimdışı sözlük saldırısıyla bulunabilir. HMAC + ayrı `SESSION_SECRET`
   bunu kapatır.
2. Çerez **iptal edilemez**: parola değişmeden çıkış yaptırmanın yolu yok, 12 saat
   dolana kadar geçerli kalır.

Demo için kabul edilebilir; gerçek kullanıcı hesaplarına geçilirse yeniden yazılmalı.

### A6. Kötüye kullanım

| Senaryo | Bugünkü davranış | Değerlendirme |
|---|---|---|
| "Çöz"e art arda basmak | `drafts.py:140` — süren koşu varsa yenisi açılmıyor, mevcut `run_id` dönüyor | **Korumalı** (aynı taslak için) |
| **Farklı taslakları aynı anda çözmek** | Koruma **yok**. Her çözüm `asyncio.to_thread` ile CP-SAT'ı `num_workers=8` ile 60 sn çalıştırır | **Açık risk.** 3 taslak = 24 çözücü iş parçacığı. Railway'in çekirdek sayısı bunun çok altında; API yanıt veremez hale gelir |
| **Yayınlanmış çizelgeyi çözmek** | Solver `schedule_drafts.status`'e bakmıyordu: "Çöz" yayındaki nöbeti sessizce değiştirebiliyordu. E-09 yayınlanmışı salt okunur gösteriyor ama solver o korumanın dışındaydı | **Kapatıldı** (28.09): `POST /solve` yayınlanmış taslakta 409 döner, arayüz "Bu çizelge yayında. Değiştirmek için önce kopya oluşturun." yazar |
| Silme uçları | 7 adet DELETE (`taslak`, `personel`, `izin`, `istek`, `uyumsuzluk`, `sözleşme`, `ihtiyaç satırı`). Hepsi token arkasında, onay gerektirmiyor | Orta — token'ı olan her istek kalıcı veri silebilir. `assignments` FK'si `RESTRICT` olduğu için ataması olan personel silinemiyor (pasife alınıyor), bu iyi |
| Hata mesajları | Ham veritabanı hatası dışarı verilmiyor; `setup.py:130` dışında `detail=str(hata)` kalıbı yok. Solver hataları `solver_diagnostics`'e yazılıyor, HTTP yanıtına değil | **Temiz** |
| **Yarıda kalan koşu** | `repositories/drafts.py:89` süren koşuyu `status='CALISIYOR'` ile arar, **zaman aşımı yok** | **Açık risk.** Railway süreci yeniden başlarsa (deploy, çökme, uyku) arka plan görevi ölür ama satır `CALISIYOR` kalır. Çift tıklama koruması bu ölü satırı bulup döndürür → **o taslak bir daha hiç çözülemez.** Elle `UPDATE solver_runs SET status='HATA'` gerekir |
| Hız sınırı (rate limit) | **Yok** | Demo için kabul edilebilir, token korumasıyla birlikte |

### A7. Kişisel veri

20 gerçek hemşirenin **adı ve soyadı** repoda dört dosyada geçiyor:

| Dosya | İçerik |
|---|---|
| `db/seeds/007_staff_seed.sql` | 20 kişi: ad, rol, çalışma tipi, yetkinlikler, kişisel notlar |
| `db/seeds/008_decisions_2026_09_24.sql` | İsimle düzeltmeler |
| `db/seeds/009_reference_week_2026_09_21.sql` | Kağıt çizelgenin birebir aktarımı |
| `docs/kisit-katalogu.md` | "Merve Armut yalnızca gündüz çalışır" |

Repo **private**, yani dağıtım yok. Ama:
- Ekran görüntüleri `docs/screenshots/live/` altında ve **`.gitignore`'da** — doğru karar.
- `docs/screenshots/` altındaki **eski faz görüntüleri commit edilmiş** ve içlerinde
  gerçek adlar var (`faz2-cizelge-1440.png` vb.).
- Repo ileride açılırsa ya da bir işbirlikçi eklenirse bu veri onunla paylaşılır.

Sağlık kuruluşu personel verisi olduğu için, hastaneyle paylaşılacak bir depoda
adların takma adlarla değiştirilmesi (`seeds/007` içinde bir eşleme tablosu)
düşünülmeli. Karar Baran'ın.

### A8. Yedek ve geri dönüş

**Doğrulanamadı — Neon panelinden kontrol edilmeli.** Neon'un ücretsiz planında
*point-in-time restore* penceresi genelde 24 saat, ücretli planlarda 7-30 gün.

Migration öncesi yedek için önerilen iki yol:

```bash
# 1) Neon branch (saniyeler sürer, en güvenlisi):
#    Neon paneli → Branches → "Create branch" → adı: yedek-2026-09-28-migration-014
#    Sorun çıkarsa branch'i ana dal yapıp geri dönülür.

# 2) Dosyaya döküm (yerelde saklanır):
pg_dump "postgresql://...neon.tech/neondb?sslmode=require" \
  --no-owner --no-privileges -Fc -f yedek-2026-09-28.dump
```

Bugünkü durumda `db/scripts/migrate.sh` migration'ları tek tek ve **her birini
kendi transaction'ında** uyguluyor (`--single-transaction`), yarıda kalırsa şema
bozulmuyor. Ama seed'ler için böyle bir koruma yok: seed'ler kendi `BEGIN/COMMIT`
bloklarını taşıyor ve hepsi bu şekilde yazılmış değil (013, 014 taşımıyor).

---

## B) KODA GÖMÜLÜ DEĞERLER

Sınıflar: **(1)** veritabanına taşınmalı · **(2)** kodda kalabilir (teknik) ·
**(3)** ortam ayarı olmalı

### B1. Solver

| Dosya:satır | Değer | Ne işe yarıyor | Sınıf |
|---|---|---|---|
| `solver/data.py:35` | `KAPSAMA_DISI_ROL = "sorumlu_hemsire"` | Genel mevcut sayımından hariç tutulan rol | **(1)** `roles`'a `counts_toward_crew BOOLEAN` |
| `solver/data.py:42` | `VARDIYA_KISITLARI = {"GUNDUZ_CMT": ("sorumlu_hemsire", {6})}` | Kısa Cumartesi vardiyası yalnız sorumluya, yalnız Cumartesi | **(1)** `shift_types`'a `only_role_id` + `only_weekdays` |
| `solver/data.py:426` | `ISTEK_TURU_ESLEME = {"off_talebi": "BOS_GUN"}` | Eski istek sözlüğünden yeniye çeviri | **(2)** geçiş bitince silinir |
| `solver/model.py:61` | `EKSIK_CEZASI_YEDEK = 1_000_000` | Kuralı olmayan ihtiyaç satırı için yedek ceza | **(2)** gerçek ağırlıklar DB'de |
| `solver/model.py:67` | `ATAMA_MALIYETI = 1` | Fazladan atamayı engelleyen birim maliyet | **(1)** teknik görünüyor ama davranışı belirliyor |
| `solver/model.py:73` | `ROZET_MALIYETI = 1` | Fazladan ambulans rozetini engeller | **(1)** aynı gerekçe |
| `solver/model.py:78` | `SAAT_EKSIGI_CEZASI = 20_000` | C-004 eksik saat cezası | **(1)** C-004 katı olduğu için DB'de ağırlığı yok; soft'a çevrilirse `default_weight`'e taşınır |
| `solver/model.py:85` | `UC_FARKI_CEZALANDIR = True` | Adalet cezasının max−min parçası açık mı | **(1)** ya da (2); ölçülmüş bir ayar düğmesi |
| `solver/model.py:86` | `RASTGELE_TOHUM = 20261001` | Tekrarlanabilirlik tohumu | **(3)** |
| `solver/model.py:87` | `ISCI_SAYISI = 8` | CP-SAT işçi sayısı | **(3)** Railway'in çekirdek sayısına göre değişmeli |
| `solver/model.py:92` | `TAM_SAYILI_GOREVLER = {"AMBULANS"}` | Üst sınırı katı olan görevler | **(1)** `need_template_rows`'a `max_count` |
| `solver/model.py:96` | `SORUMLU_CUMARTESI = "GUNDUZ_CMT"` | Sorumlunun Cumartesi vardiyası | **(1)** C-008'e parametre |
| `solver/model.py:97`, `validate.py:30` | `SORUMLU_ROL = "sorumlu_hemsire"` | Sabit programlı rol | **(1)** B1'in ilk satırıyla aynı çözüm |
| `solver/model.py:105` | `C016_ASGARI_BILINEN_GUN = 4` | C-016'nın uygulanması için gereken bilinen gün | **(1)** C-016'ya `constraint_params` satırı |
| `solver/model.py:108`, `validate.py:28` | `GECMIS_GUN = 7` | Geçmişe bakış penceresi | **(1)** ya da (2); kuralların gerektirdiği en uzun geri bakış |
| `solver/model.py` (C-009 bloğu) | `"TRIYAJ"`, `"GOZLEM"`, `"AMBULANS"` metinleri | Alan adları | **(2)** `competencies.code` ile eşleşiyor, ama kodda sabit |
| `solver/stub.py:24` | `REFERANS_TASLAK = "Referans: elle hazırlanan 21-27 Eylül"` | Stub'ın kopyaladığı taslak, **ada göre** | **(1)** `schedule_drafts`'a `is_reference BOOLEAN` |
| `solver/aciklama.py:34-40`, `inspect.py:16-18` | `VARDIYA_ADI`, `SLOT_ADI`, ay/gün adları | Türkçe etiketler | **(2)** sunum metni |

### B2. API

| Dosya:satır | Değer | Ne işe yarıyor | Sınıf |
|---|---|---|---|
| `app/rapor.py:15,17` · `routers/demand.py:20` · `routers/schedule.py:20` | `VARDIYA_ADI`, `SLOT_ADI`, `VARDIYA_ETIKET` | Kod → Türkçe etiket | **(1)** `shift_types.name` zaten var; slot adları için `need_template_rows`'a `label` |
| `routers/export.py:176,180` · `routers/schedule.py:32` | `{"sorumlu_hemsire", "egitim_hemsire", "shift_yetkilisi"}` | Izgara satır gruplaması | **(1)** `roles`'a `display_group` + `sort_order` |
| `repositories/*.py` (6 dosya) | `WHEN 'sorumlu_hemsire' THEN 1` sıralama | Personel listelerinde rol sırası | **(1)** aynı çözüm: `roles.sort_order` |
| `repositories/demand.py:14` · `overview.py:32` | `ntr.slot_code = 'GENEL'` | Kapsama sayımı hangi slottan | **(2)** `GENEL` şemanın kendi sözlüğünde |
| `schemas/schedule.py:136` | `Literal["GUNDUZ","GECE","IZIN","BOS"]` | Hücre vardiya kodu | **(1)** vardiya tipi eklenirse tip güncellenmeli |
| `schemas/people.py:10` | `RuleType = Literal["off_talebi","acilis_tercihi","kapanis_tercihi"]` | İstek türleri — **ESKİ SÖZLÜK** | **(1)** acil: yeni sözlükle (BOS_GUN…) uyuşmuyor, bkz. C bölümü |
| `app/settings.py:22` | `solver_time_limit_s = 60` | Çözüm süresi | **(3)** ✅ zaten `.env`'de |

### B3. Web

| Dosya:satır | Değer | Sınıf |
|---|---|---|
| `components/cizelge/HucreDuzenle.tsx:15,56` | `"GUNDUZ"`, `"GECE"` seçenekleri | **(1)** `/shift-types` ucundan çekilmeli |
| `lib/personel.ts:21-23` | `off_talebi`, `acilis_tercihi`, `kapanis_tercihi` etiketleri | **(1)** eski sözlük |
| `lib/api-types.ts` | Üretilmiş tipler | **(2)** `openapi-typescript` çıktısı |

### B4. En kritik üç tanesi

1. **`RuleType` eski sözlükte** — veritabanı `BOS_GUN / SADECE_GUNDUZ / SADECE_GECE`
   ve `KESIN / MUMKUNSE` biliyor, API ve web hâlâ `off_talebi` gönderiyor. Yeni
   istek modeli **arayüzden hiç kullanılamıyor**.
2. **`SORUMLU_ROL` / `KAPSAMA_DISI_ROL`** — "sorumlu hemşire" kavramı beş dosyada
   metin olarak gömülü. Rol kodu değişirse solver sessizce yanlış çizelge üretir.
3. **`ISCI_SAYISI = 8`** — Railway'de kaç çekirdek olduğu bilinmiyor. Çekirdekten
   fazla işçi CP-SAT'ı yavaşlatır.

---

## C) ARAYÜZDEN DEĞİŞTİRİLEBİLİRLİK

Hedef: **hiçbir kalıcı değişiklik için SQL yazmak gerekmesin.**

| Veri | Tablo | Ekle | Düzenle | Sil | Ekran | Eksikse ne gerekiyor |
|---|---|---|---|---|---|---|
| Personel | `staff` | ✅ | ✅ | ✅ (pasife alma) | E-02 | — |
| Rol | `roles` | ❌ | ❌ | ❌ | — (yalnız liste) | CRUD uç + ekran. Rol eklemek bugün SQL ister |
| Sözleşme / hedef saat | `contracts` | ✅ | ✅ | ✅ | E-02 detay | — |
| Yetkinlik **tanımı** | `competencies` | ❌ | ❌ | ❌ | — (yalnız liste) | CRUD uç + ekran. Yeni yetkinlik (örn. "ÇOCUK ACİL") SQL ister |
| Yetkinlik **kişiye atama** | `staff_competencies` | ✅ | ✅ (`PUT`) | ✅ | E-04 matris | — |
| Vardiya tipi (saat, süre, aktif) | `shift_types` | ❌ | ❌ | ❌ | E-05 (salt okunur) | CRUD uç + ekran. 24 saatlik vardiyayı açmak (C-018) bugün SQL ister |
| İhtiyaç şablonu (başlık) | `need_templates` | ❌ | ❌ | ❌ | E-06 (liste) | "Bayram Haftası" şablonu açmak SQL ister |
| İhtiyaç satırı (kaç kişi) | `need_template_rows` | ✅ | ✅ | ✅ | E-06 | — |
| Satırın istediği yetkinlik | `need_template_row_competencies` | ❌ | ❌ | ❌ | — | HASTA_ILT'i kaldırmak seed gerektirdi |
| **İhtiyaç dönemi** | `need_periods` | ❌ | ❌ | ❌ | — | Hangi tarihte hangi şablon geçerli — **hiç açık değil** |
| Kural (hard/soft, ağırlık) | `constraints` | ❌ | ✅ (`PATCH`) | ❌ | E-03 | Yeni kural eklemek seed ister (kabul edilebilir: kurala kod da lazım) |
| Kural parametresi | `constraint_params` | ❌ | ✅ (`PATCH`) | ❌ | E-03 | Yeni parametre eklemek seed ister |
| İzin / rapor | `absences` | ✅ | ✅ | ✅ | E-02 detay | — |
| **İstek (tür + güç)** | `availability_rules` | ⚠️ | ❌ | ✅ | E-02 detay | **Tür eski sözlükte, güç (KESIN/MUMKUNSE) hiç yok.** `RuleType` güncellenmeli, `status` API'ye ve ekrana eklenmeli, `PATCH` ucu açılmalı |
| Uyumsuz çift | `staff_conflicts` | ✅ | ❌ (not) | ✅ | E-02 detay | Not düzenleme yok — küçük |
| Personel notu | `staff.note` | ✅ | ✅ | ✅ | E-02 | — |
| Oryantasyon + eşi | `staff.is_orientation`, `buddy_staff_id` | ✅ | ✅ | ✅ | E-02 | — |
| Sadece gündüz/gece | `staff.shift_eligibility` | ✅ | ✅ | ✅ | E-02 | — |
| Taslak | `schedule_drafts` | ✅ | ✅ | ✅ | E-08 | — |
| Atama (hücre) | `assignments` | ✅ | ✅ | ✅ | E-09 | — |

### C1. Özet

**SQL gerektiren 7 şey var:**

1. **İhtiyaç dönemi** (`need_periods`) — hangi tarihte hangi şablon. Hiçbir uç yok.
2. **İstek türü ve gücü** — yeni sözlük arayüzden kullanılamıyor.
3. **Vardiya tipi** — saat, süre, aktif/pasif. 24 saatlik vardiyayı açmak imkânsız.
4. **Yetkinlik tanımı** — yeni bir yetkinlik eklenemiyor.
5. **İhtiyaç satırının istediği yetkinlik** — köprü tablo açık değil.
6. **Rol** — yeni rol eklenemiyor.
7. **İhtiyaç şablonu başlığı** — ikinci bir şablon açılamıyor.

Bunların **1 ve 2**'si sunumda karşılaşılması muhtemel; 3-7 daha uzak ihtimal.

---

## ÖNCELİK

### Canlıdan önce şart

| # | İş | Gerekçe |
|---|---|---|
| 1 | **Railway'de `DEMO_API_TOKEN` dolu mu doğrula** | Boşsa API tamamen açık |
| 2 | **Neon'da yedek/branch al** (migration 014, 015 + seed 013-016 öncesi) | Geri dönüş yolu |
| 3 | **`/health`'in migration kontrolünü 015'e kadar genişlet** | Bugün yalnız 013'ü yokluyor; 014/015 eksikse canlı sessizce yanlış çalışır |
| 4 | **Eşzamanlı çözüm sınırı** | Birden çok taslak aynı anda çözülürse Railway boğulur |
| 5 | **`ISCI_SAYISI`'nı ortam ayarına taşı** | Railway'in çekirdek sayısına göre ayarlanmalı |
| 6 | **Yarıda kalan koşuya zaman aşımı** | Deploy sırasında çözüm koşuyorsa o taslak kalıcı olarak kilitlenir (bkz. A6) |

### Sunumdan önce iyi olur

| # | İş | Gerekçe |
|---|---|---|
| 6 | **İstek türü + gücü arayüze** (`RuleType`, `status`, `PATCH` ucu) | Yeni istek modeli kullanılamıyor; E-10'da "karşılanamayan tercihler" var ama tercih girilemiyor |
| 7 | `/docs` ve `/redoc`'u canlıda kapat | API yüzeyi herkese açık |
| 8 | **Ayrı veritabanı kullanıcısı** (`nobet_app`) | Uygulama sahip yetkisiyle çalışmamalı |
| 9 | `need_periods` için uç + ekran | Şablon dönemini değiştirmek SQL istiyor |

### Sunumdan sonra

| # | İş |
|---|---|
| 10 | `SORUMLU_ROL` / `GUNDUZ_CMT` kuralını veritabanına taşı (`roles.counts_toward_crew`, `shift_types.only_role_id`) |
| 11 | Vardiya tipi, yetkinlik tanımı, rol, şablon başlığı için CRUD |
| 12 | Çerez imzasını HMAC + ayrı `SESSION_SECRET` ile kur, çıkış ucu ekle |
| 13 | Ceza sabitlerini (`ATAMA_MALIYETI`, `ROZET_MALIYETI`, `SAAT_EKSIGI_CEZASI`, `C016_ASGARI_BILINEN_GUN`) veritabanına taşı |
| 14 | Gerçek personel adları için takma ad kararı |
| 15 | Hız sınırı, gizli bilgi rotasyon adımları |
