-- seeds/019_oryantasyon_takviye.sql
-- 28.09.2026: Oryantasyon acil takviye kuralı (C-022).
--
-- Oryantasyondaki personel normalde genel mevcuda SAYILMAZ (migration 009).
-- İSTİSNA: bir vardiyanın genel mevcudu başka türlü tamamlanamıyorsa
-- (örn. 4/5), oryantasyondaki biri 5. kişi olarak yazılabilir.
--
-- SON ÇARE OLMASI AĞIRLIKLA SAĞLANIR: 500.000, eksik cezasının (2.000.000)
-- ALTINDA, diğer her şeyin (en yüksek O-006 = 22.000) ÜSTÜNDE. Eksik varsa
-- takviye kullanmak 2.000.000 kazandırıp 500.000 ödetir — kullanılır.
-- Eksik yoksa 500.000'i boşuna ödetir — asla kullanılmaz.
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source, catalog_code)
VALUES ('orientation_emergency_backup', 'Oryantasyon acil takviye',
        'Genel mevcut başka türlü tamamlanamıyorsa oryantasyondaki personel son çare '
        'olarak vardiyaya yazılabilir. Ambulansa çıkmaz, triyaj/gözlem yetkin sayımına '
        'katılmaz, alanda yalnız bırakılmaz ve eğitim hemşiresiyle eşleşme (C-020) '
        'bu durumda aranmaz. Diğer güvenlik kuralları (dinlenme, haftalık izin, '
        'çalışma tipi) geçerlidir.',
        FALSE, 500000, 'vardiya', 'kurumsal', 'C-022')
ON CONFLICT (code) DO NOTHING;
