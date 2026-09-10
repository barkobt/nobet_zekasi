# nobet_zekasi
# Nöbet Zekası - Veritabanı Mimarisi

Bu repo, Nöbet Zekası projesinin ilişkisel veri tabanı tasarımı, şema sürümleri ve migration süreçlerini içerir.

## Ortam & Altyapı
- **RDBMS:** PostgreSQL 16+
- **Veritabanı Adı:** `nobet_zekasi`
- **Gerekli Eklentiler:** `btree_gist` (Zaman aralıkları ve çakışma kısıtları / EXCLUDE constraints için)

## Migration Stratejisi & Gerekçe
- **Seçilen Yöntem:** Numaralandırılmış düz `.sql` dosyaları (`migrations/` dizini altında).
- **Gerekçe:** 
  - ORM abstraction katmanına ihtiyaç duymadan PostgreSQL'in gelişmiş özelliklerini (özel tipler, `EXCLUDE USING gist`, fonksiyonlar, trigger'lar) saf SQL ile doğrudan yönetmek.
  - Şema üzerindeki tüm DDL işlemlerinde tam denetim sağlamak ve DBeaver/psql üzerinden deterministik bir yürütme sırası izlemek.

## Dizin Yapısı

nobet_zekasi/
├── README.md
└── migrations/
    ├── 001_init_schema.sql
    └── ...

--
