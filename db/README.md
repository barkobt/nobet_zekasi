# Nöbet Zekâsı — Veritabanı

PostgreSQL şeması: numaralı migration dosyaları + seed verisi.

## Klasörler

| Klasör | İçerik | Kural |
|---|---|---|
| `migrations/` | Yapı (`CREATE`, `ALTER`, `DROP`) | Çalışmış dosya düzenlenmez, yeni numara eklenir |
| `seeds/` | Başlangıç verisi (`INSERT`) | Tekrar çalıştırılabilir olmalı (çift kayıt üretmez) |
| `queries/` | Kontrol ve rapor sorguları | Hiçbir şeyi kalıcı değiştirmez |

## Ortam ve altyapı

- **RDBMS:** PostgreSQL 16+ (geliştirmede 18.4, Neon'da yönetilen sürüm)
- **Veritabanı adı:** `nobet_zekasi` (yerel)
- **Gerekli eklenti:** `btree_gist` — zaman aralıkları ve çakışma kısıtları
  (`EXCLUDE USING gist`) için. Migration 005 kuruyor, Neon destekliyor.

## Migration stratejisi ve gerekçe

**Yöntem:** numaralandırılmış düz `.sql` dosyaları. ORM ve migration aracı yok.

**Neden:**
- ORM soyutlamasına girmeden PostgreSQL'in gelişmiş özelliklerini saf SQL ile
  doğrudan yönetmek: `EXCLUDE USING gist`, üretilen kolonlar, kısmi indeksler,
  view'lar, trigger'lar.
- Şemadaki her DDL üzerinde tam denetim ve DBeaver/psql üzerinden deterministik
  yürütme sırası.
- Şema tek doğruluk kaynağıdır; API katmanı onu tekrar tanımlamaz.

## Sıfırdan kurulum sırası

1. `migrations/001` → `009` arası tüm `.up.sql` dosyaları, numara sırasıyla
2. `seeds/001` → `009`, numara sırasıyla
3. `queries/checks.sql` ile doğrulama, `queries/reference_week_audit.sql` ile gerçek çizelge denetimi

## Geri alma

`.down.sql` dosyaları **ters** sırayla: 009 → 001.

## Katmanlar

| Katman | Migration | Tablolar |
|---|---|---|
| 0 · Referans | 001–004 | units, shift_types, competencies, constraints, constraint_params |
| 1 · Kadro | 005 | roles, staff, contracts, staff_competencies, availability_rules, absences, staff_conflicts |
| 2 · İhtiyaç | 006 | need_templates, need_template_rows, need_template_row_competencies, need_periods |
| 3 · Çözüm | 007 | schedule_drafts, solver_runs, assignments, assignment_tasks, solver_diagnostics, actual_times |
| Bütünlük + raporlar | 008 | staff.is_active, CHECK'ler, 5 view |
| Kapsama düzeltmesi | 009 | v_daily_coverage: sorumlu ve oryantasyon GENEL mevcuda sayılmaz |
| Yetkinlik türü | 010 | competencies.kind (TASK/QUALIFICATION), katalog kodu, ihtiyaç↔kural bağı, uygunluk trigger'ı |
| Triyaj/gözlem modeli | 011 | TRIYAJ–GÖZLEM ayrıklık trigger'ı, kapsamaya `qualified` ve `remaining_after_ambulance` |

## Görünümler (view)

| View | Ekran | Ne gösterir |
|---|---|---|
| `v_staff_conflict_pairs` | E-04 | Uyumsuz çiftler, iki yönlü |
| `v_assignment_hours` | — | Atama başına planlanan / gerçekleşen / geç çıkış saati |
| `v_monthly_hours` | E-11 | Kişi × ay puantajı, eksik saat, iki fazla mesai tanımı |
| `v_fairness` | E-12 | Gece / hafta sonu sayısı, ortalamadan sapma |
| `v_daily_coverage` | E-09 | Gün × vardiya × slot: atanan / gereken |

## Seed'ler ve migration'lar arasındaki fark

Migration çalıştıktan sonra düzenlenmez. Seed ise **güncel doğruyu** anlatır ve düzenlenebilir,
yeter ki tekrar çalıştırılabilir kalsın. Sahadan gelen kararlar tarihli seed olarak eklenir
(`008_decisions_2026_09_24.sql`), böylece "o gün ne değişti?" sorusunun cevabı tek dosyada durur.

| Seed | İçerik |
|---|---|
| 007 | Gerçek kadro (20 kişi), yetkinlikler, sözleşmeler, oryantasyon eşleşmesi |
| 008 | 24.09 kararları: ambulans kuralı, sayım zorunluluğu, gündüz mevcudu 5 (sorumlu ve oryantasyon hariç) |
| 009 | Elle hazırlanan referans çizelge (21–27 Eylül 2026) |
| 010 | Katalog kodları (C-001…O-002), ihtiyaç satırı ↔ kural bağı |
| 011 | C-009 tek kurala çevrildi, "her çalışan triyaj veya gözlemde" kuralı, referans haftanın triyaj/gözlem rozetleri kuraldan türetildi |
