-- 013_assignment_source_referans.up.sql
-- 27.09.2026: assignments.source'a 'referans' değeri eklendi.
--
-- SORUN: 'manuel' dört ayrı durumda yazılıyordu ve hepsi aynı şey sayılıyordu:
--   1) kağıt çizelgenin aktarımı (seeds/009)
--   2) yeni taslağa başlangıç verisi kopyalama
--   3) taslak kopyalama
--   4) kullanıcının ızgara hücresinden yaptığı düzenleme
-- "Taslağı uygula" onayı "mevcut çizelgede N elle yapılmış değişiklik var" derken
-- dördünü birden sayıyordu: kopyalanmış bir çizelgede 91 atamanın hepsi "elle
-- değişiklik" görünüyordu. Oysa kullanıcı hiçbirine dokunmamıştı.
--
-- Artık 1-3 'referans', yalnız 4 'manuel'.
--
-- DAVRANIŞ DEĞİŞMEYEN YERLER:
--   * Solver yalnız source='solver' satırları siler → 'referans' korunmaya devam eder.
--   * assignment_tasks trigger'ları source='solver' ise HATA, değilse UYARI verir;
--     'referans' da uyarı tarafında kalır (Güven Göl kaydı yine geçer).

ALTER TABLE assignments DROP CONSTRAINT ck_assignments_source;

ALTER TABLE assignments
    ADD CONSTRAINT ck_assignments_source
    CHECK (source IN ('solver', 'manuel', 'referans', 'onceki_ay'));

COMMENT ON COLUMN assignments.source IS
    'solver: çözücü üretti · manuel: kullanıcı ızgaradan düzenledi · '
    'referans: kağıttan/başka taslaktan kopyalandı · onceki_ay: değiştirilemez bağlam';

-- Mevcut veriyi taşı: kullanıcı düzenlemeleri KİLİTLİdir (hucre_yaz is_locked=TRUE
-- yazar), kopyalananlar ise yalnızca lock_seeded seçilmişse kilitlidir. Ayırt etmek
-- için güvenilir tek iz bu değil — bu yüzden mevcut 'manuel' satırların tamamını
-- 'referans' kabul ediyoruz: bugün veritabanındaki tek 'manuel' küme seeds/009'dan
-- gelen kağıt aktarımıdır ve o zaten referanstır.
UPDATE assignments SET source = 'referans' WHERE source = 'manuel';
