# Nöbet Zekâsı — Acıbadem Smart Planner

Acıbadem Kent ASG acil servisi için CP-SAT tabanlı hemşire nöbet planlama sistemi.
İç kod adı **Nöbet Zekâsı**, dışarıya **Acıbadem Smart Planner**.
Hedef: 1 Ekim 2026, hastane yöneticilerine canlı link üzerinden demo.

## Monorepo

| Klasör | İçerik |
|---|---|
| `db/` | PostgreSQL şeması: `migrations/`, `seeds/`, `queries/`, `scripts/` |
| `api/` | FastAPI servisi + solver |
| `web/` | Next.js arayüzü |
| `docs/` | Ekran haritası, kısıt kataloğu, `brand/` logoları, `mockups/` düzen taslakları |

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
- Beklenen: 22 tablo, 6 view, 20 personel, 91 atama, 1 bilinen uygunluk ihlali.
- `db/seeds/009` kağıt çizelgenin birebir aktarımıdır; **gerçeği kurala uydurmak için
  değiştirilmez.** İçindeki bilinen ihlal `v_task_eligibility_violations`'ta görünür.

## API

- FastAPI, paket yönetimi **uv**, DB erişimi **psycopg 3** (`AsyncConnectionPool`, `dict_row`).
- Katmanlar: `routers/` (HTTP) → `repositories/` (SQL). `schemas/` yalnızca Pydantic
  API sözleşmesidir, iş mantığı taşımaz.
- Ayarlar `pydantic-settings` ile.
- Solver çalıştırma: POST ile `solver_runs` kaydı + `BackgroundTasks`; frontend GET ile
  durum yoklar. **Kuyruk sistemi (Celery/Redis) YOK.**
- `api/solver/model.py` **Baran'ındır, dokunulmaz.** Aramızdaki sözleşme
  `api/solver/interface.py`: `run_solver(draft_id: int, time_limit_s: int = 60) -> SolveResult`
  (senkron, kendi DB bağlantısını açar).
- Veritabanı zaten uyguladığı kuralları (tekillik, çakışma, CHECK) API'de tekrarlama;
  hatayı yakala ve Türkçeye çevir.

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
