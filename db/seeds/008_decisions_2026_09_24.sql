-- seeds/008_decisions_2026_09_24.sql
-- 24.09.2026 saha kararları (Edem). Hepsi VERİ değişikliği: şema ve solver kodu değişmez.
-- Tarihli seed: "o gün ne değişti?" sorusunun cevabı bu dosya. Tekrar çalıştırılabilir.

BEGIN;

-- 1) Kadro düzeltmeleri (eski 007'yi çalıştırmış olanlar için; yeni 007'de zaten doğru)
INSERT INTO staff_competencies (staff_id, competency_id)
SELECT s.id, c.id
FROM (VALUES ('Şükran Ünlü', 'SHIFT_YETKILISI'),
             ('Halit Güler', 'SAYIM')) AS x (full_name, competency_code)
JOIN staff s        ON s.full_name = x.full_name
JOIN competencies c ON c.code = x.competency_code
ON CONFLICT (staff_id, competency_id) DO NOTHING;

UPDATE staff SET shift_eligibility = 'sadece_gunduz'
WHERE full_name = 'Merve Armut' AND shift_eligibility <> 'sadece_gunduz';

-- 2) Ambulans kuralı değişti: "Ambulans ile triyaj alakasız."
--    Eski: ambulans ekibi triyaj havuzundan çıkar.
--    Yeni: ambulans ekibi triyajdan da gözlemden de çıkabilir, ama 2 kişinin en fazla 1'i gözlemden.
--          (Gözlemde 2 kişi var; ikisi birden ambulansa çıkarsa gözlem boş kalır.)
--    Eski satır varsa ve yeni henüz yoksa: kodunu ve metnini güncelle (id'si korunur).
--    Yeni satır zaten varsa (güncel 003 çalıştıysa): eskisini sil.
UPDATE constraints
SET code        = 'ambulance_observation_limit',
    name        = 'Ambulans–gözlem sınırı',
    description = 'Ambulans görevindeki kişilerden en fazla 1''i gözlem alanından çıkabilir, diğeri triyajdan. Ambulans için triyaj yetkinliği şart değil.'
WHERE code = 'ambulance_from_triage_pool'
  AND NOT EXISTS (SELECT 1 FROM constraints WHERE code = 'ambulance_observation_limit');

DELETE FROM constraints WHERE code = 'ambulance_from_triage_pool';

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'max_ambulance_from_observation', 1, 'Aynı vardiyada gözlemden ambulansa çıkabilecek en fazla kişi'
FROM constraints WHERE code = 'ambulance_observation_limit'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

UPDATE constraints
SET description = 'Triyajda en az 3 yetkin kişi bulunmalı.'
WHERE code = 'triage_pool_min_size';

-- 3) Sayım yetkilisi her vardiyada zorunlu (sorumlu hemşire de sayabilir).
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source)
VALUES ('count_authority_required', 'Sayım yetkilisi zorunluluğu',
        'Her vardiyada en az 1 sayım yetkili kişi bulunmalı', TRUE, NULL, 'vardiya', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

-- 4) Kısa gece (çizelgedeki "GECE(01:00)"): modele ALINMADI (24.09 kararı: "gece 1'ler yok, boşver").

-- 5) İhtiyaç şablonu güncellemeleri
--    a) Gündüz genel mevcut 6 → 5: "6'nın 1'i sadece sorumlu" demek, çalışan hemşire 5 demek.
--       Sorumlu ve oryantasyondakiler bu 5'e SAYILMAZ (sayımı v_daily_coverage yapıyor, migration 009).
UPDATE need_template_rows ntr
SET min_count = 5,
    note = 'Genel mevcut, sorumlu hariç (sorumlu varsa +1)'
FROM need_templates nt, shift_types st
WHERE nt.id = ntr.need_template_id AND st.id = ntr.shift_type_id
  AND nt.code = 'standart' AND st.code = 'GUNDUZ' AND ntr.slot_code = 'GENEL'
  AND ntr.min_count = 6;

--    b) Her vardiyaya SAYIM slotu (en az 1)
WITH raw (shift_code) AS (VALUES ('GUNDUZ'), ('GECE'))
INSERT INTO need_template_rows (need_template_id, shift_type_id, slot_code, min_count, note)
SELECT nt.id, st.id, 'SAYIM', 1, 'En az 1 sayım yetkilisi'
FROM raw
JOIN units u           ON u.code = 'ACIL_SERVIS'
JOIN shift_types st    ON st.unit_id = u.id AND st.code = raw.shift_code
JOIN need_templates nt ON nt.code = 'standart'
ON CONFLICT (need_template_id, shift_type_id, slot_code) DO NOTHING;

INSERT INTO need_template_row_competencies (need_template_row_id, competency_id)
SELECT ntr.id, c.id
FROM need_template_rows ntr
JOIN need_templates nt ON nt.id = ntr.need_template_id AND nt.code = 'standart'
JOIN competencies c    ON c.code = 'SAYIM'
WHERE ntr.slot_code = 'SAYIM'
ON CONFLICT (need_template_row_id, competency_id) DO NOTHING;

COMMIT;
