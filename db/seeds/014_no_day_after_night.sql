-- seeds/014_no_day_after_night.sql
-- 28.09.2026: Gece çalışan ertesi gün gündüze yazılamaz. (C-021)
--
-- NEDEN YENİ KURAL: C-001'e göre gündüz 08:30–18:00, gece 18:00–08:30 ve
-- "aralarında boşluk yok". Gece d gününde 18:00'de başlar, d+1'de 08:30'da biter;
-- d+1'in gündüzü de 08:30'da başlar. Yani gece sonrası gündüz = sıfır dinlenme,
-- fiilen 24 saat kesintisiz çalışma.
-- C-014'ten farkı: o İKİ gece sonrasını düzenler, bu TEK gece sonrasını.
--
-- KAYNAK 'kurumsal' (yasal değil): 24 saatlik vardiya tipi açıldığında (C-018) ya da
-- elle düzenlemede bu geçiş meşru olabilir, o yüzden E-03'te gevşetilebilmeli.
--
-- catalog_code C-021: katalogda C-001…C-020 dolu, sıradaki boş kod bu.
-- Parametresi yok — kuralın söylediği tek şey "yasak".
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source, catalog_code)
VALUES ('no_day_shift_after_night', 'Gece sonrası gündüz yasağı',
        'Gece vardiyasında çalışan kişi ertesi gün gündüz vardiyasına yazılamaz. '
        'Gece 08:30''da biter, gündüz 08:30''da başlar: arada dinlenme yoktur.',
        TRUE, NULL, 'kisi', 'kurumsal', 'C-021')
ON CONFLICT (code) DO NOTHING;

-- Daha önce kurulmuş bir veritabanında satır varsa metni/kaynağı güncel tut.
UPDATE constraints
SET name         = 'Gece sonrası gündüz yasağı',
    source       = 'kurumsal',
    catalog_code = 'C-021'
WHERE code = 'no_day_shift_after_night'
  AND (source, catalog_code) IS DISTINCT FROM ('kurumsal', 'C-021');
