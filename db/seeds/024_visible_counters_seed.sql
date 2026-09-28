-- 024_visible_counters_seed.sql
-- Görünür sayaçlar ve varsayılan açık/kapalı durumları (hastane ile kararlaştırıldı).
--
-- G, N, S her zaman görünür: "Detayları göster" kapalıyken de satırda durur.
-- Diğerleri yalnız "Detayları göster" AÇIK ve burada o görünüm için AÇIK ise görünür.
-- Haftalık ve aylık ayrı ayarlanır: haftalık görünümde 4 hafta sonu sayacı
-- anlamsız, aylıkta anlamlı.
--
-- Tekrar çalıştırılabilir: anahtar üzerinden UPSERT, ama kullanıcının SONRADAN
-- yaptığı açma/kapamayı EZMEZ — yalnız eksik satırı ekler, metinleri günceller.

BEGIN;

INSERT INTO visible_counters (key, badge, label, description, sort_order,
                              always_shown, weekly_on, monthly_on) VALUES
  ('G',   'G',   'Gündüz vardiya sayısı',     'Görünen dönemde gündüz vardiyası sayısı',              10, TRUE,  TRUE,  TRUE),
  ('N',   'N',   'Gece vardiya sayısı',       'Görünen dönemde gece vardiyası sayısı',                20, TRUE,  TRUE,  TRUE),
  ('S',   'S',   'Toplam saat',               'Görünen dönemde planlanan toplam çalışma saati',       30, TRUE,  TRUE,  TRUE),
  ('HF',  'HF',  'Hedefe fark (saat)',        'Dönem hedefine uzaklık; eksikse negatif',              40, FALSE, FALSE, TRUE),
  ('TRY', 'TRY', 'Triyaj sayısı',             'Triyaj görevi verilen vardiya sayısı',                 50, FALSE, FALSE, FALSE),
  ('GOZ', 'GÖZ', 'Gözlem sayısı',             'Gözlem görevi verilen vardiya sayısı',                 60, FALSE, FALSE, FALSE),
  ('AMB', 'AMB', 'Ambulans sayısı',           'Ambulans görevi verilen vardiya sayısı',               70, FALSE, FALSE, FALSE),
  ('HS',  'HS',  'Hafta sonu çalışılan gün',  'Cumartesi ve Pazar çalışılan gün sayısı',              80, FALSE, FALSE, TRUE),
  ('PZ',  'PZ',  'Çalışılan Pazar sayısı',    'Yalnız Pazar günü çalışılan vardiya sayısı',           90, FALSE, FALSE, FALSE),
  ('BG',  'BG',  'Boş gün sayısı',            'Hiç vardiya başlamayan gün sayısı (izin dahil)',      100, FALSE, FALSE, FALSE),
  ('IST', 'İST', 'Karşılanamayan tercih',     'Mümkünse isteklerinden karşılanamayanların sayısı',   110, FALSE, FALSE, FALSE)
ON CONFLICT (key) DO UPDATE
   SET badge        = EXCLUDED.badge,
       label        = EXCLUDED.label,
       description  = EXCLUDED.description,
       sort_order   = EXCLUDED.sort_order,
       always_shown = EXCLUDED.always_shown;
       -- weekly_on / monthly_on BİLEREK güncellenmiyor: kullanıcı ayarı korunur.

COMMIT;
