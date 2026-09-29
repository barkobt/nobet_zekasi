# Deploy — Neon + Railway + Vercel

Demo canlı link üzerinden yapılacak; yerelde çalıştırma seçeneği yok.
Zincir: **Neon** (veritabanı) → **Railway** (api) → **Vercel** (web).

---

## ⚠ DEPLOY GIT PUSH İLE OLMUYOR

**Ne Railway ne Vercel GitHub'a bağlı.** `git push` hiçbir deploy tetiklemez —
kod GitHub'a gider, canlı eski sürümde kalır ve bu sessizce olur.

Her ikisi de **CLI ile elden** deploy edilir:

```bash
# API — api/ klasöründen
cd api && railway up

# Web — web/ klasöründen
cd web && vercel --prod --yes
```

**Deploy ettiğini nasıl anlarsın:**

```bash
# API: yeni kod aktifse "kullanici" alanı gelir
curl -s https://nobet-zekasi-api-production.up.railway.app/api/health

# Web: en üstteki satırın yaşı (Age) dakikalar içinde olmalı
cd web && vercel ls --yes | head -5
```

Railway'de `railway up` **çalışma dizinini yükler**, git'i okumaz: commit edilmemiş
değişiklikler de gider. Deploy etmeden önce `git status --short` boş olsun.

İleride GitHub'a bağlamak istenirse: Railway → servis → Settings → Source →
Connect Repo (Root Directory `api`), Vercel → Project → Settings → Git. Bu
yapılana kadar **her deploy elle**.

---

Sıra önemli: web, API'nin adresini ister; API, veritabanının adresini ister.

---

## İki ayrı bağlantı dizesi — karıştırma

Neon iki uç verir ve **aynı iş için kullanılmazlar**:

| Değişken | Uç | Ne için | Nerede |
|---|---|---|---|
| `DATABASE_URL_DIRECT` | `ep-xxx.eu-central-1.aws.neon.tech` (pooler **yok**) | Şema ve seed kurulumu | Yalnız yerelde, kurulum anında. Hiçbir yere kaydedilmez. |
| `DATABASE_URL` | `ep-xxx-**pooler**.eu-central-1.aws.neon.tech` | Uygulamanın çalışma anı bağlantısı | Railway ortam değişkeni |

**Neden:** pooled uç PgBouncer'ın *transaction* modunda çalışır — bağlantı her
ifadeden sonra başka bir istemciye geçebilir. Şema kurulumu buna dayanmaz:
`CREATE EXTENSION btree_gist` (migration 005), `CREATE TEMP TABLE` (seeds/007 ve 009)
ve uzun transaction'lar oturumun aynı kalmasını ister. Uygulama tarafı ise tam tersine
havuzdan faydalanır (kısa, bağımsız sorgular).

`db/scripts/rebuild.sh` bu ayrımı bilir: `DATABASE_URL_DIRECT` varsa onu kullanır,
pooled bir uç verilirse uyarır.

---

## 1) Neon — veritabanı  *(Baran yapıyor)*

1. https://console.neon.tech → **New Project**
   - Bölge: **AWS eu-central-1 (Frankfurt)** — İstanbul'a en yakın olan, gecikme demoda hissedilir
   - Postgres sürümü: varsayılan
2. **Connection Details** panelinde iki dizeyi de al:
   - *Connection pooling* **kapalı** → `DATABASE_URL_DIRECT` (kurulum için)
   - *Connection pooling* **açık** → `DATABASE_URL` (Railway için, içinde `-pooler` geçer)
3. Şemayı ve verileri kur (yerelde, repo kökünde):

   ```bash
   DATABASE_URL_DIRECT="postgresql://...@ep-xxx.eu-central-1.aws.neon.tech/neondb?sslmode=require" \
     ./db/scripts/rebuild.sh --yes
   ```

**Beklenen çıktı:**

```
 tablo | view | personel | atama | uygunluk_ihlali
-------+------+----------+-------+-----------------
    22 |    6 |       20 |    91 |               1
Bitti. Beklenen: 22 tablo, 6 view, 20 personel, 91 atama, 1 uygunluk ihlali.
```

`seeds/009` sırasında **tek bir WARNING** görürsün (Güven Göl / AMBULANS) — beklenen.
Kağıt çizelgedeki gerçek bir tutarsızlığın kaydı, hata değil.

---

## 2) Railway — API  *(kuruldu)*

Proje: **nobet-zekasi-api** · Adres: **https://nobet-zekasi-api-production.up.railway.app**

```bash
cd api
railway init --name nobet-zekasi-api --json
railway up --detach
railway variables --set "SOLVER_IMPL=stub" --set "SOLVER_TIME_LIMIT_S=60" \
                  --set "DB_POOL_MIN=1" --set "DB_POOL_MAX=10" --skip-deploys
```

Railway `api/railway.json`'daki başlangıç komutunu ve `/api/health` sağlık kontrolünü kullanır.
Servis ayarlarında **Root Directory = `api`** olmalı.

Deploy sonrası Railway'in verdiği alan adını not al (`https://xxx.up.railway.app`).

**Doğrulama:** `curl https://<railway-url>/api/health` → `{"status":"ok","db":true,"tablo":22,...}`

---

## 3) Vercel — web  *(kuruldu)*

Proje: **acibadem-smart-planner** · Adres: **https://acibadem-smart-planner.vercel.app**

```bash
cd web
vercel link --yes --project acibadem-smart-planner
printf 'https://nobet-zekasi-api-production.up.railway.app' | vercel env add API_BASE_URL production
vercel --prod --yes
```

**Doğrulama:** `https://<vercel-url>/` → şifre ekranı.

---

## Ortam değişkenleri — kim neyi nereye giriyor

`DEMO_API_TOKEN`'ı üret (Baran, kendi terminalinde):

```bash
openssl rand -hex 32
```

Aynı değer hem Railway'e hem Vercel'e girilir; ikisi eşleşmezse API 401 döner.

| Değişken | Servis | Değer | Giren |
|---|---|---|---|
| `DATABASE_URL` | Railway | Neon **pooled** dizesi (`-pooler` içerir) | **Baran** — dashboard |
| `DEMO_API_TOKEN` | Railway | `openssl rand -hex 32` çıktısı | **Baran** — dashboard |
| `SOLVER_IMPL` | Railway | `cpsat` | Claude — CLI |
| `SOLVER_WORKERS` | Railway | Railway'in vCPU sayısı (varsayılan 8 fazla olabilir) | Claude — CLI |
| `SOLVER_MAX_CONCURRENT` | Railway | `1` | Claude — CLI |
| `ENVIRONMENT` | Railway | `production` (dokümantasyon uçlarını kapatır) | Claude — CLI |
| `SOLVER_TIME_LIMIT_S` | Railway | `60` | Claude — CLI ✅ |
| `DB_POOL_MIN` / `DB_POOL_MAX` | Railway | `1` / `10` | Claude — CLI ✅ |
| `DB_POOL_MAX_IDLE` / `DB_POOL_MAX_LIFETIME` | Railway | `120` / `240` (Neon uykusundan kısa) | varsayılan yeterli |
| `API_BASE_URL` | Vercel | `https://nobet-zekasi-api-production.up.railway.app` | Claude — CLI ✅ |
| `DEMO_API_TOKEN` | Vercel | Railway'dekiyle **birebir aynı** | **Baran** — dashboard |
| `DEMO_PASSWORD` | Vercel | Yöneticilere verilecek demo şifresi | **Baran** — dashboard |

Vercel'de üçü de **Production** ortamına girilir ve hiçbiri `NEXT_PUBLIC_` önekli
**değildir** — sunucuda kalır, tarayıcıya inmezler.

Baran "girdim" dedikten sonra redeploy edilir (`railway up`, `vercel --prod`) ve
aşağıdaki kabul kontrolü yapılır.

---

## Canlı kabul kontrolü

1. `https://nobet-zekasi-api-production.up.railway.app/api/health`
   → `{"status":"ok","db":true,"tablo":22,"view":6,"aktif_personel":20}`
2. `https://acibadem-smart-planner.vercel.app/` → şifre ekranı çıkmalı
3. Yanlış şifre → "Şifre hatalı." · doğru şifre → `/personel`, Neon'dan **20 kişi**
4. Tarayıcı ağ sekmesinde Railway adresi ve `DEMO_API_TOKEN` **görünmemeli**
   (tüm istekler `<vercel-url>/api/...` adresine gitmeli)
5. 1440px genişlikte ekran görüntüsü

---

---

## Canlıda şema güncelleme — `migrate.sh`

**Neon'da `rebuild.sh` KULLANILMAZ.** O şemayı siler; elle girilen personel,
izin ve çizelge verisi kaybolur. `rebuild.sh` artık uzak bir adres görürse
kendiliğinden durur ve seni buraya yönlendirir.

Canlıda doğru araç `migrate.sh`: yalnız **uygulanmamış** migration'ları,
her birini kendi transaction'ında uygular. Uyguladıklarını `schema_migrations`
tablosunda tutar, ikinci çağrıda atlar. Veriye dokunmaz.

```bash
# Ne uygulanmış, ne bekliyor?
DATABASE_URL_DIRECT="postgresql://...@ep-xxx.neon.tech/neondb?sslmode=require" \
  ./db/scripts/migrate.sh --status

# Bekleyenleri uygula
DATABASE_URL_DIRECT="postgresql://...@ep-xxx.neon.tech/neondb?sslmode=require" \
  ./db/scripts/migrate.sh
```

### Mevcut Neon'u bir kereye mahsus işaretle

Neon'daki şema 001–012 ile kuruldu ama `schema_migrations` defteri yok.
Bu komut **hiçbir SQL çalıştırmaz**, yalnız "bunlar uygulanmış" diye kaydeder:

```bash
DATABASE_URL_DIRECT="postgresql://...@ep-xxx.neon.tech/neondb?sslmode=require" \
  ./db/scripts/migrate.sh --mark-applied
```

Bundan sonra yeni bir migration eklendiğinde yalnız `migrate.sh` yeter.

> Seed'ler canlıda **yalnız ilk kurulumda** koşar (`--seed`). Her seed dosyası
> deftere yazılır; ikinci çağrıda atlanır, böylece elle girilen verinin üstüne
> yazılmaz.

### Canlıya tek bir veri seed'i eklemek

Sonradan eklenen bir veri seed'ini (örn. demo taslağı) şemaya ve mevcut veriye
dokunmadan, **yalnız bir kez** çalıştırır:

```bash
DATABASE_URL_DIRECT="postgresql://...@ep-xxx.neon.tech/neondb?sslmode=require" \
  ./db/scripts/migrate.sh --seed-file 012_demo_draft.sql
```

İkinci çağrıda "zaten çalışmış, atlandı" der. `--mark-applied` seed'leri
bilerek işaretlemez; sonradan eklenen veri seed'leri bu komutla koşabilsin diye.

---

## Demo günü güvenliği — Neon branch'i

Neon'da branch, veritabanının o andaki **yazılabilir kopyası**. Sunum sabahı
çalışan bir kopyayı kenara koy; bir şey bozulursa Railway'i ona çevir.

### Yedek branch'i oluştur (sunumdan önce)

1. https://console.neon.tech → projen → sol menüden **Branches**
2. **New Branch**
3. **Name:** `demo-yedek`
4. **Parent branch:** `production` (ya da ana branch'in adı ne ise)
5. **Include data up to:** *Current point in time*
6. **Create branch**
7. Branch açılınca **Connection Details** → **Pooled connection** dizesini kopyala
   ve kenara al. Buna yalnız acil durumda ihtiyacın olacak.

### Sunumda sorun çıkarsa — yedeğe geç

1. https://railway.com → **nobet-zekasi-api** → **Variables**
2. `DATABASE_URL` satırında kalem ikonuna bas
3. Değeri `demo-yedek` branch'inin **pooled** dizesiyle değiştir
4. **Save** — Railway kendiliğinden yeniden dağıtır (~40 sn)
5. `https://nobet-zekasi-api-production.up.railway.app/api/health` → `db: true`
   ve `sema_guncel: true` gördüğünde hazırsın

### Geri dön (sunumdan sonra)

1. Aynı ekranda `DATABASE_URL`'i **asıl** branch'in pooled dizesiyle değiştir
2. **Save**, sağlık kontrolünü tekrar yap

> Branch'ler bağımsızdır: `demo-yedek`'te yapılan değişiklik asıl veritabanına
> geçmez. Sunumda oraya bağlıyken girilen veri, geri dönünce görünmez.

## Neden bu yapı?

- **API proxy** (`web/src/app/api/[...path]/route.ts`): tarayıcı yalnızca kendi
  origin'indeki `/api/...` adresini görür. Railway adresi ve `DEMO_API_TOKEN` istemci
  paketine hiç girmez, ayrıca Railway tarafında CORS ayarı gerekmez.
- **Tek ortak şifre** (`web/src/proxy.ts`): şifre sunucuda kalır, tarayıcıya yalnızca
  SHA-256 imzası HttpOnly çerez olarak gider.
- **`SOLVER_IMPL` anahtarı**: `model.py` bittiğinde Railway'de bu değişkeni `cpsat`
  yapmak yeterli; API ve web kodu değişmez.

## Tip üretimi

API sözleşmesi değişince web tiplerini yenile:

```bash
cd web && pnpm gen:api                                  # yerel API'den
API_BASE_URL=https://<railway-url> pnpm gen:api         # canlı API'den
```


---

## Şu anki durum (25.09.2026)

| Aşama | Durum |
|---|---|
| Neon — proje | ⏳ Baran'da |
| Neon — şema kurulumu | ⏳ Son deneme yerel veritabanına gitti, Neon'a değil |
| Railway — proje + build | ✅ Railpack `uv`'yi tanıdı, `libpq` kurdu |
| Railway — çalışma | ❌ `DATABASE_URL` yok → açılışta havuz kurulamıyor, 502 |
| Vercel — proje + deploy | ✅ Ready |
| Vercel — API proxy zinciri | ✅ Kanıtlandı: `/api/health` Railway'in 502'sini birebir iletiyor |
| Gizli değişkenler | ⏳ Baran dashboard'dan girecek |

`DEMO_PASSWORD` girilene kadar site şifresizdir: kök adres `/personel`e yönlenir.
Şifre girilince `/giris`e yönlenmeye başlar.

---

## Çözüm kalitesi — işçi sayısı ve ipucu tuzağı

**29.09.2026'da öğrenilenler.** Aynı veri, aynı kurallarla canlıda Ekim'in saat
farkı 23 sa çıkarken yerelde 3 sa çıkıyordu. İki ayrı sebep vardı:

### 1. SOLVER_WORKERS

Railway'de `SOLVER_WORKERS=2` ayarlıydı. CP-SAT'ta paralel işçiler **farklı arama
stratejileri** deniyor; işçi sayısı çözüm kalitesini süreden daha çok belirliyor:

| İşçi | Süre | Amaç | Saat farkı |
|---:|---:|---:|---:|
| 2 | 60 sn | 7.145.398 | 18,5 sa |
| 2 | 180 sn | 3.191.111 | 18,5 sa |
| 8 | 60 sn | 585.497 | **3,0 sa** |

Süreyi üçe katlamak yetmiyor, işçi sayısı belirleyici. Railway konteyneri
48 çekirdek görüyor; ayar **8**'e çekildi. `/api/health` artık `cekirdek` ve
`solver_isci` alanlarını döndürüyor — bu fark bir daha veri sorunu sanılmasın.

### 2. İpucu + erken durdurma birlikte kilitliyor

Çözüm, taslakta duran atamaları başlangıç ipucu olarak kullanıyor (gerileme
olmasın diye). Ama kaynak kötüyse ipucu aramayı o kötü yerde tutuyor:

- Kötü bir Ekim'den (80,5 sa) kopyalanıp çözülünce 22 sa'da kilitlendi.
- Süre 300 sn verilse bile koşu 20-37 sn'de bitiyordu: ipucu anında bulunuyor,
  `SOLVER_NO_IMPROVEMENT_S` (15 sn) iyileşme göremeyip aramayı durduruyor.
- **Boş taslakla (ipuçsuz) aynı ay 3,0 sa** verdi — makine yeterliydi.

**Kural:** "kopyala → çöz" akışı kaynağın kalitesini miras alır. Kötü bir
çizelgeden başlanıyorsa **boş taslak açıp sıfırdan çözmek** gerekir.
Canlıda `SOLVER_NO_IMPROVEMENT_S` 60'a çekildi.
