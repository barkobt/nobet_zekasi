# Clinorq

Erişkin acil servis için CP-SAT tabanlı hemşire nöbet planlama sistemi.
Ürün adı her yerde **Clinorq** (logoda küçük harf: `clinorq`). Hastanenin adı,
logosu ve hiçbir marka öğesi üründe, kodda ya da dokümanda geçmez — yasal
zorunluluk (29.09.2026). Kurum adı bir ayardır (E-14), koda gömülmez.
Hedef: 1 Ekim 2026, hastane yöneticilerine canlı link üzerinden demo.

## Monorepo

| Klasör | İçerik |
|---|---|
| `db/` | PostgreSQL şeması: `migrations/`, `seeds/`, `queries/`, `scripts/` |
| `api/` | FastAPI servisi + solver |
| `web/` | Next.js arayüzü |
| `docs/` | Ekran haritası, kısıt kataloğu, `brand/clinorq/` logo seti, `mockups/` düzen taslakları |

## Veritabanı

- **`db/migrations` altındaki çalışmış dosyalar ASLA düzenlenmez.** Şemada eksik
  görürsen dur ve yeni bir migration öner; onay almadan uygulama.
- Şema tek doğruluk kaynağıdır. **ORM ve Alembic YOK** — psycopg 3 + düz SQL.
- `migrations/` = yapı (`CREATE`, `ALTER`, `DROP`). `seeds/` = veri (`INSERT`, `UPDATE`),
  düzenlenebilir ama **tekrar çalıştırılabilir** kalmalı (çift kayıt üretmez).
- Tüm migration'lar tüm seed'lerden önce koşar. Bir migration mevcut satırları
  dolduramaz (o anda tablolar boştur) — sınıflandırma/varsayılan veri seed'e yazılır.
- Sıfırdan kurulum: `./db/scripts/rebuild.sh` (yerel) veya
  `DATABASE_URL="postgres://..." ./db/scripts/rebuild.sh --yes` (Neon).
- Sıfırdan kurulumda beklenen: **26 tablo** (migrate.sh ile 27 — fark `schema_migrations`,
  aracın kendi defteri), **7 view**, 22 personel (20 aktif), 882 atama, 13 uygunluk ihlali.
  İhlallerin 1'i referans haftasından, 12'si kağıt Eylül'den gelir; ikisi de gerçektir.
- `db/seeds/009` kağıt çizelgenin birebir aktarımıdır; **gerçeği kurala uydurmak için
  değiştirilmez.** İçindeki bilinen ihlal `v_task_eligibility_violations`'ta görünür.

## API

- FastAPI, paket yönetimi **uv**, DB erişimi **psycopg 3** (`AsyncConnectionPool`, `dict_row`).
- Katmanlar: `routers/` (HTTP) → `repositories/` (SQL). `schemas/` yalnızca Pydantic
  API sözleşmesidir, iş mantığı taşımaz.
- Ayarlar `pydantic-settings` ile.
- Solver çalıştırma: POST ile `solver_runs` kaydı + `BackgroundTasks`; frontend GET ile
  durum yoklar. **Kuyruk sistemi (Celery/Redis) YOK.**
- Kişiye özel çalışma deseni `staff_weekly_patterns`'ta **veri**dir — sorumlunun sabit
  programı dahil. Solver'da kişi adı, gün numarası ya da rol adı gömülü DEĞİL;
  kapsama dışı rol de `roles.counts_toward_coverage` bayrağından okunur.
- **Kapsama ile 200 saat havuzu ayrı sorular.** Kapsamaya sayılmamak (ekip kadrosunun
  yerine geçmemek) hedefsiz kalmak demek değildir. Havuz dışı olmanın gerekçesi sabit
  programlı ya da oryantasyonda olmaktır.
- **Saat birimi DAKİKA.** Molalar mesaiye dahil değil; net süre tek yerde tanımlı
  (`v_shift_types_net`), her tüketici oradan okur. Solver da dakikayla çalışır
  (`solver/data.py` → `_dk`). Saate çevirme yalnız GÖSTERİM içindir: gündüzün neti
  8 sa 10 dk, saat cinsinden devirli ondalık — ara hesapta yuvarlanırsa toplam kayar.
- Solver'ın API ile sözleşmesi `api/solver/interface.py`:
  `run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult`
  (senkron, kendi DB bağlantısını açar). Ayrıntısı `docs/solver-contract.md`.
- Veritabanı zaten uyguladığı kuralları (tekillik, çakışma, CHECK) API'de tekrarlama;
  hatayı yakala ve Türkçeye çevir.

## Solver çalışma şekli

- Solver adım adım yazılır; her adım Baran'ın onayıyla ilerler.
- Her adımda ÖNCE planı sade Türkçeyle anlat (ne yapacaksın, neden böyle), kod yazmadan
  dur ve onay bekle.
- Onaydan sonra kodu yaz ve çalıştır.
- Raporda kritik kod parçalarını göster (SQL sorguları, veri yapısı, kurallar). Her
  parçanın altında 2-3 cümleyle ne yaptığını sade dille açıkla. Standart/tekrar eden
  kodu gösterme, sadece "şunlar da var" de.
- Emin olmadığın bir şeyi tahmin etme; "Sorular" başlığında sor.

### Adım sırası

| Adım | Kapsam |
|---|---|
| 1 | Veriyi oku (`data.py`, `inspect.py`) — bitti |
| 2 | En basit çizelge: günde 1 vardiya, kapsama, sorumlunun programı — bitti |
| 3 | Asla bozulmayan kurallar (C-002, C-014, C-016, C-020, gece→gündüz yasağı) + kontrolcü (`validate.py`) |
| 4 | Görevler: triyaj, gözlem, ambulans |
| 5 | Adalet (O-002) ve 200 saat (C-004, O-001) |
| 5b | Molalar mesaiye dahil değil → net saat (migration 023) — bitti |
| 5c | İzin desenleri C-023/C-024 + kişiye özel haftalık desen (migration 024) — bitti |
| 6 | Eksik açıklamaları (teşhis metinleri) |

Adalet Adım 3 DEĞİL, Adım 5'tir.

## Web

- Next.js (App Router) + TypeScript + Tailwind + shadcn/ui, paket yöneticisi **pnpm**.
- Veri: TanStack Query. Izgaralar (E-02, E-09): TanStack Table.
- Tipler `openapi-typescript` ile FastAPI'nin `/openapi.json`'undan üretilir — elle yazılmaz.

## Arayüz

Arayüzle ilgili her işten önce kökteki DESIGN.md'yi oku; tek tasarım
kaynağı odur. Logolar docs/brand/ altında, kullanımı DESIGN.md §4.1'de.
Mockup'lar yalnızca düzen referansıdır.

## Genel kurallar

- Scaffolding için resmi araçları kullan (`create-next-app`, `uv init`, `shadcn init`);
  config dosyalarını elle yazma.
- Gizli bilgiler `.env`'de. `.env.example` commit edilir, `.env` edilmez.
- Arayüz metinleri Türkçe. Terimler: *vardiya*, *taslak*, *yetkinlik*, *ekip lideri*,
  *sorumlu hemşire*, *eğitim hemşiresi*, *oryantasyon*. Tarih `21 Eyl 2026`, sayı `4.158`.
- Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`.
- Deploy: Neon (Postgres, pooled, `sslmode=require`) · Railway (api) · Vercel (web).
