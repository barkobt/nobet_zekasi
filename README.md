# Clinorq

Erişkin acil servis için CP-SAT tabanlı hemşire nöbet planlama sistemi.

Kurallar veritabanında yaşar, kodda değil: "bu ay gece kuralını gevşetelim" demek için
deploy gerekmez. Çözücü aylık çalışır, çizelge haftalık gösterilir.

## Monorepo

| Klasör | Ne var | Nasıl çalıştırılır |
|---|---|---|
| `db/` | PostgreSQL şeması: 10 migration, 10 seed, 22 tablo, 6 view | `./db/scripts/rebuild.sh` |
| `api/` | FastAPI + psycopg 3 + CP-SAT solver | `cd api && uv run fastapi dev app/main.py` |
| `web/` | Next.js + TypeScript + Tailwind + shadcn/ui | `cd web && pnpm dev` |
| `docs/` | Ekran haritası, kısıt kataloğu, marka varlıkları, düzen taslakları | — |

Tasarım dili: kökteki [`DESIGN.md`](DESIGN.md).
Çalışma kuralları: [`CLAUDE.md`](CLAUDE.md).

## Hızlı başlangıç

```bash
# 1) Veritabanı
createdb nobet_zekasi
./db/scripts/rebuild.sh --yes
# Beklenen: 22 tablo, 6 view, 20 personel, 91 atama, 1 uygunluk ihlali

# 2) API
cd api && uv sync && uv run fastapi dev app/main.py   # → http://localhost:8000

# 3) Web
cd web && pnpm install && pnpm dev                    # → http://localhost:3000
```

Uzak veritabanı için: `DATABASE_URL="postgres://..." ./db/scripts/rebuild.sh --yes`

## Kapsam

**MVP (1 Ekim 2026 demosu):** E-01 Vardiya Tanımları · E-02 Yetkinlik Matrisi ·
E-03 Kural Seti · E-04 Personel · E-06 İhtiyaç Şablonu · E-08 Taslaklar ·
E-09 Nöbet Çizelgesi (ana ekran) · E-10 Çözüm Teşhisi

**Sonraki faz:** E-05 İzin Yönetimi · E-07 Dönem Planlaması · E-11 Saat Bütçesi · E-12 Adalet Panosu

Ayrıntı: [`docs/ekran-haritasi.md`](docs/ekran-haritasi.md) ve
[`docs/kisit-katalogu.md`](docs/kisit-katalogu.md).
