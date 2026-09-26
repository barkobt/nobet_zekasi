# Deploy — Neon + Railway + Vercel

Demo canlı link üzerinden yapılacak; yerelde çalıştırma seçeneği yok.
Zincir: **Neon** (veritabanı) → **Railway** (api) → **Vercel** (web).

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
| `SOLVER_IMPL` | Railway | `stub` | Claude — CLI ✅ |
| `SOLVER_TIME_LIMIT_S` | Railway | `60` | Claude — CLI ✅ |
| `DB_POOL_MIN` / `DB_POOL_MAX` | Railway | `1` / `10` | Claude — CLI ✅ |
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
