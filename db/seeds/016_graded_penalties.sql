-- seeds/016_graded_penalties.sql
-- 28.09.2026: Eksik cezaları kademeli, yeni yumuşak tercihler (O-006…O-008),
-- triyaj slotundan HASTA_ILT şartının kaldırılması.
--
-- 1) KADEMELİ EKSİK CEZALARI
--    Şimdiye kadar her eksik aynı fiyattaydı (kodda tek sabit). Artık kural
--    başına ayrı ağırlık var ve ağırlıklar VERİTABANINDA — E-03'ten ayarlanır.
--    Sıra (büyükten küçüğe): genel mevcut > ekip lideri > triyaj > ambulans
--    mevcudu > gözlem > sayım.
--
--    NEDEN is_hard ARTIK FALSE: bu kuralları solver zaten gevşetiyordu (eksik
--    kalırsa çizelge yine üretiliyor, eksik büyük cezayla sayılıyor). Katalog
--    "Hard" diyor ama gerçek davranış "çok pahalı ama gevşetilebilir". CHECK
--    kısıtı ağırlıklı kuralın soft olmasını istiyor; DB artık gerçeği söylüyor.
--    C-009 İSTİSNA: ambulans sonrası alanda kalan kuralı KATI kalıyor.
--
--    Değerler hastane teyidi beklemektedir; açıklamalara da yazıldı.

BEGIN;

-- Ambulans MEVCUDU ile ambulans SONRASI KALAN artık ayrı kurallar.
-- C-009 "kalan" tarafını anlatıyor ve katı; mevcut sayısı gevşetilebilir olmalı.
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source)
VALUES ('ambulance_crew_size', 'Ambulans ekip mevcudu',
        'Ambulans görevine vardiya başına 2 kişi çıkar (sayı ihtiyaç şablonunda). '
        'Üst sınır katıdır: araç 2 kişiliktir, fazlası hatadır. Alt sınır '
        'gevşetilebilir. Ağırlık hastane teyidi beklemektedir.',
        FALSE, 900000, 'vardiya', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

-- Ambulans ihtiyaç satırları yeni kurala bağlanır (C-009 yalnız "kalan" kuralı olur).
UPDATE need_template_rows ntr
SET constraint_id = c.id
FROM constraints c
WHERE c.code = 'ambulance_crew_size' AND ntr.slot_code = 'AMBULANS'
  AND ntr.constraint_id IS DISTINCT FROM c.id;

-- Kademeli ağırlıklar. UPDATE koşulsuz → tekrar çalıştırılabilir.
UPDATE constraints c
SET is_hard        = FALSE,
    default_weight = m.agirlik,
    description    = c.description || ' [Eksik cezası hastane teyidi beklemektedir.]'
FROM (VALUES
    ('day_shift_min_crew',             2000000),
    ('night_shift_min_crew',           2000000),
    ('shift_lead_required',            1500000),
    ('triage_pool_min_size',           1200000),
    ('all_crew_triage_or_observation',  600000),
    ('observation_pool_separate',       700000),
    ('count_authority_required',        500000)
) AS m (code, agirlik)
WHERE c.code = m.code AND c.is_hard;

-- Yalnız ağırlık güncellemesi (zaten soft ise açıklamayı bir daha ekleme)
UPDATE constraints c
SET default_weight = m.agirlik
FROM (VALUES
    ('day_shift_min_crew',             2000000),
    ('night_shift_min_crew',           2000000),
    ('shift_lead_required',            1500000),
    ('triage_pool_min_size',           1200000),
    ('all_crew_triage_or_observation',  600000),
    ('observation_pool_separate',       700000),
    ('count_authority_required',        500000),
    ('ambulance_crew_size',             900000)
) AS m (code, agirlik)
WHERE c.code = m.code AND c.default_weight IS DISTINCT FROM m.agirlik;

-- 2) TRIYAJ SLOTU YALNIZ TRIYAJ YETKİNLİĞİ İSTER
--    HASTA_ILT bir triyaj ÖN KOŞULU değil, TERCİHİ (O-007). Şart olarak durunca
--    hasta iletişimi olmayan bir triyaj yetkilisi havuzdan tamamen düşüyordu.
DELETE FROM need_template_row_competencies x
USING need_template_rows ntr, competencies c
WHERE x.need_template_row_id = ntr.id AND x.competency_id = c.id
  AND ntr.slot_code = 'TRIYAJ' AND c.code = 'HASTA_ILT';

-- 3) YENİ YUMUŞAK TERCİHLER
--    O-006'nın ağırlığı: bir karşılanmayan istek ≈ saat adaletinde 5 saatlik
--    bozulma. O-002 yarım saat başına 2.200 → 5 sa = 10 yb → 10 × 2.200 = 22.000.
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source, catalog_code)
VALUES
  ('staff_request_penalty', 'Karşılanamayan tercihler',
   '"Mümkünse" (MUMKUNSE) güçteki istekler karşılanmaya çalışılır; karşılanamayan her '
   'tercih cezalandırılır. "Kesin" (KESIN) istekler katı kuraldır, buraya girmez. '
   'Ağırlık: bir karşılanmayan tercih ≈ saat adaletinde 5 saatlik bozulma.',
   FALSE, 22000, 'kisi', 'tercih', 'O-006'),

  ('triage_communication_preference', 'Triyajda hasta iletişimi tercihi',
   'Triyaj görevine mümkünse hasta iletişimi (HASTA_ILT) yetkinliği olanlar yazılır. '
   'Şart değil, tercihtir: olmayan biri triyajda çalışırsa küçük ceza uygulanır.',
   FALSE, 2200, 'vardiya', 'tercih', 'O-007'),

  ('ambulance_area_split', 'Ambulans ekibi alan dağılımı',
   'Ambulansa çıkan 2 kişi mümkünse 1 triyajdan + 1 gözlemden olur. İkisi aynı '
   'alandan çıkarsa küçük ceza uygulanır. C-009 (her alanda en az 1 kişi kalır) '
   'katı kuraldır ve ayrıdır; triyajdan 2 kişi çıkmak yasak değildir.',
   FALSE, 2200, 'vardiya', 'tercih', 'O-008')
ON CONFLICT (code) DO NOTHING;

-- Ad ve açıklama güncellemesi (ON CONFLICT DO NOTHING var olan satırı değiştirmez)
UPDATE constraints
SET name = 'Karşılanamayan tercihler',
    description = '"Mümkünse" (MUMKUNSE) güçteki istekler karşılanmaya çalışılır; '
                  'karşılanamayan her tercih cezalandırılır. "Kesin" (KESIN) istekler '
                  'katı kuraldır, buraya girmez. Ağırlık: bir karşılanmayan tercih ≈ '
                  'saat adaletinde 5 saatlik bozulma.'
WHERE code = 'staff_request_penalty' AND name <> 'Karşılanamayan tercihler';

COMMIT;
