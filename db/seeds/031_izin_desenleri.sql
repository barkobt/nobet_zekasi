-- 031_izin_desenleri.sql
-- Bölüm 3: izin (off) desenleri. Edem + Baran kararları, 29.09.2026.
--
-- Hepsi VERİ: kural metni, parametresi ve kişiye özel desen burada durur.
-- Solver bunları okur; koda gömülü tek bir gün, sayı ya da isim yoktur.
--
-- Tekrar çalıştırılabilir: ON CONFLICT DO NOTHING / koşullu UPDATE.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Kapsamaya sayılmayan roller
-- ---------------------------------------------------------------------------
-- Sorumlu hemşire zaten sayılmıyordu (migration 009). Eğitim hemşiresi de
-- çıkarılıyor (Baran, 29.09): Şükran her hafta kesin gelir ama 5 kişilik ekip
-- kadrosunun yerine geçmez — oryantasyondakini yetiştirmekle meşgul.
UPDATE roles SET counts_toward_coverage = FALSE
WHERE code IN ('sorumlu_hemsire', 'egitim_hemsire');

-- ---------------------------------------------------------------------------
-- 2) Yeni kurallar
-- ---------------------------------------------------------------------------
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source) VALUES
    ('day_only_weekly_off',
     'Gündüzcü haftalık izin',
     'Sadece gündüz çalışan personel haftada TAM 1 gün izin yapar (6 gün çalışır). '
     'İzin günü haftanın herhangi bir günü olabilir; hafta Pazartesi–Pazar takvim haftasıdır. '
     '2 ya da 3 gün izin kullanılmaz.',
     TRUE, NULL, 'hafta', 'kurumsal'),
    ('max_consecutive_off',
     'Ardışık izin sınırı',
     'Üst üste en fazla 2 gün boş kalınır. Yıllık izin, rapor ve planlayıcının '
     'girdiği kesin izin istekleri bu sınırın dışındadır — onlar bloğu uzatabilir.',
     TRUE, NULL, 'kisi', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

UPDATE constraints SET catalog_code = 'C-023' WHERE code = 'day_only_weekly_off'  AND catalog_code IS NULL;
UPDATE constraints SET catalog_code = 'C-024' WHERE code = 'max_consecutive_off' AND catalog_code IS NULL;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, 'day_only_weekly_off', 1,
       'Gündüzcünün haftalık izin gün sayısı. TAM bu kadar olmalı, en az/en çok değil.'
FROM constraints c WHERE c.code = 'day_only_weekly_off'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, 'max_consecutive_off', 2,
       'Üst üste izinsiz boş gün üst sınırı. İzin/rapor/kesin istek günleri sayılmaz.'
FROM constraints c WHERE c.code = 'max_consecutive_off'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 3) Halit Güler (sorumlu hemşire) — sabit haftalık program
-- ---------------------------------------------------------------------------
-- C-008 metniyle aynı; farkı, artık solver/model.py'de kod değil burada veri.
-- Pzt–Cum gündüz · Cmt 08:30–14:00 kısa vardiya · Paz kesin izin.
INSERT INTO staff_weekly_patterns (staff_id, isodow, kind, shift_type_id, note)
SELECT s.id, d.isodow, 'SABIT_VARDIYA', st.id, 'C-008 sorumlu hemşire programı'
FROM staff s
CROSS JOIN (VALUES (1),(2),(3),(4),(5)) AS d(isodow)
JOIN shift_types st ON st.code = 'GUNDUZ'
WHERE s.full_name = 'Halit Güler'
ON CONFLICT (staff_id, isodow) DO NOTHING;

INSERT INTO staff_weekly_patterns (staff_id, isodow, kind, shift_type_id, note)
SELECT s.id, 6, 'SABIT_VARDIYA', st.id, 'C-008 Cumartesi 08:30–14:00'
FROM staff s
JOIN shift_types st ON st.code = 'GUNDUZ_CMT'
WHERE s.full_name = 'Halit Güler'
ON CONFLICT (staff_id, isodow) DO NOTHING;

INSERT INTO staff_weekly_patterns (staff_id, isodow, kind, shift_type_id, note)
SELECT s.id, 7, 'SABIT_OFF', NULL, 'C-008 Pazar kesin izin'
FROM staff s WHERE s.full_name = 'Halit Güler'
ON CONFLICT (staff_id, isodow) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 4) Şükran Ünlü (eğitim hemşiresi) — haftalık izni hafta sonuna sabit
-- ---------------------------------------------------------------------------
-- Haftada 1 gün izin yapar (C-023) ama o gün Cumartesi ya da Pazar olmak
-- zorunda (Baran, 29.09). Hangisi olacağını solver seçer.
INSERT INTO staff_weekly_patterns (staff_id, isodow, kind, shift_type_id, note)
SELECT s.id, d.isodow, 'OFF_OLABILIR', NULL, 'Haftalık izin Cmt ya da Paz olmalı'
FROM staff s
CROSS JOIN (VALUES (6),(7)) AS d(isodow)
WHERE s.full_name = 'Şükran Ünlü'
ON CONFLICT (staff_id, isodow) DO NOTHING;

COMMIT;
