-- seeds/007_staff_seed.sql
-- GERÇEK KADRO (Edem'den, 24.09.2026) — 20 kişi.
-- Notion'daki 18 kişilik örnek listenin yerine geçer.
-- Eski (örnek) 007'yi çalıştırdıysan ÖNCE queries/cleanup_mock_staff.sql'i çalıştır.
--
-- KALIP: ETL. Ham veri staging tablosuna → oradan gerçek tablolara dönüştürülerek.
-- Tüm dosya tek transaction: hata olursa hiçbir şey yazılmaz.
--
-- Edem tabloyu 24.09.2026'da onayladı. Tek düzeltme: Şükran Ünlü ekip lideri olabilir.
-- Sevda Koç ve Muhammet Edem ambulansa çıkmıyor. Halit Güler'in sayım yetkisi var.
-- Merve Armut: sadece gündüz (24.09 kararı). Referans haftadaki 2 gecesi zorunluluktan.
-- Varsayım: IV, İM, hasta iletişimi herkeste var (oryantasyondakiler hariç).

BEGIN;

-- 0) Referans veri düzeltmeleri
--    Sayım yetkisi ekip liderliğinden AYRI bir yetkinlik (Sevda Koç: "sayım yok, ekip lideri olabilir").
INSERT INTO competencies (code, name, description)
VALUES ('SAYIM', 'Sayım yetkisi', 'Vardiya sayım yetkisi. Ekip liderliğinden ayrı.')
ON CONFLICT (code) DO NOTHING;

--    SHIFT_YETKILISI açıklamasındaki "eski adı sayım yetkilisi" notu artık yanlış.
UPDATE competencies
SET description = 'Ekip lideri: vardiyayı yönetebilir ("shift tutabilir"). Sayım yetkisinden ayrı.'
WHERE code = 'SHIFT_YETKILISI';

INSERT INTO roles (code, name)
VALUES ('egitim_hemsire', 'Eğitim Hemşiresi')
ON CONFLICT (code) DO NOTHING;

INSERT INTO shift_types (unit_id, code, name, start_time, duration_hours)
SELECT id, 'GUNDUZ_CMT', 'Gündüz (Cumartesi kısa, sorumlu)', '08:30', 5.5
FROM units WHERE code = 'ACIL_SERVIS'
ON CONFLICT (unit_id, code) DO NOTHING;

-- 1) STAGING
--    temel       = IV + İM + hasta iletişimi
--    ekip_lideri = shift tutabilir (SHIFT_YETKILISI)
--    sayim       = sayım yetkisi (SAYIM)
--    oryantasyon = eğitim sürecinde, eğitim hemşiresiyle birebir çalışır
CREATE TEMP TABLE tmp_personel (
    full_name TEXT, role_code TEXT, eligibility TEXT,
    temel BOOLEAN, triyaj BOOLEAN, gozlem BOOLEAN, ambulans BOOLEAN,
    ekip_lideri BOOLEAN, sayim BOOLEAN, oryantasyon BOOLEAN, note TEXT
) ON COMMIT DROP;

INSERT INTO tmp_personel VALUES
--  ad soyad          rol                çalışma tipi      TEMEL  TRIYAJ GÖZLEM AMB    EKİP   SAYIM  ORYANT. not
('Halit Güler',     'sorumlu_hemsire', 'sadece_gunduz',  TRUE,  FALSE, FALSE, FALSE, FALSE, TRUE,  FALSE, 'Sorumlu hemşire. Sayım yetkisi var. Pzt-Cmt gündüz.'),
('Zehra Kutucu',    'shift_yetkilisi', 'gunduz_gece',    TRUE,  TRUE,  TRUE,  FALSE, TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler, ambulans yok.'),
('Şükran Ünlü',     'egitim_hemsire',  'sadece_gunduz',  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  FALSE, 'Eğitim hemşiresi, tüm yetkinlikler, ekip lideri olabilir.'),
('Mediha Aydoğan',  'shift_yetkilisi', 'gunduz_gece',    TRUE,  FALSE, TRUE,  FALSE, TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler, ambulans ve triyaj yok.'),
('Engin Sümer',     'shift_yetkilisi', 'gunduz_gece',    TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler.'),
('Birol Karaca',    'shift_yetkilisi', 'gunduz_gece',    TRUE,  TRUE,  TRUE,  FALSE, TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler, ambulans yok.'),
('Fatih Sırcan',    'shift_yetkilisi', 'gunduz_gece',    TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler.'),
('Serpil Demir',    'hemsire',         'sadece_gunduz',  TRUE,  TRUE,  FALSE, FALSE, FALSE, FALSE, FALSE, 'Sadece triyaj. Normal gündüz personeli.'),
('Eda Karakuş',     'shift_yetkilisi', 'gunduz_gece',    TRUE,  FALSE, TRUE,  TRUE,  TRUE,  TRUE,  FALSE, 'Tüm yetkinlikler, triyaj yok.'),
('Havva Abravcı',   'hemsire',         'gunduz_gece',    TRUE,  TRUE,  TRUE,  TRUE,  FALSE, FALSE, FALSE, NULL),
('Sevda Koç',       'hemsire',         'sadece_gunduz',  TRUE,  TRUE,  TRUE,  FALSE, TRUE,  FALSE, FALSE, 'Ekip lideri olabilir, sayım yok, ambulans yok.'),
('Muhammet Edem',   'hemsire',         'gunduz_gece',    TRUE,  TRUE,  TRUE,  FALSE, FALSE, FALSE, FALSE, 'Ambulans yok.'),
('Kader Can',       'hemsire',         'gunduz_gece',    TRUE,  TRUE,  FALSE, TRUE,  FALSE, FALSE, FALSE, 'Sadece triyaj + ambulans'),
('Emre Baydilli',   'hemsire',         'gunduz_gece',    TRUE,  TRUE,  TRUE,  TRUE,  FALSE, FALSE, FALSE, NULL),
('Sıla Öner',       'hemsire',         'gunduz_gece',    TRUE,  TRUE,  TRUE,  TRUE,  FALSE, FALSE, FALSE, NULL),
('Derya Torun',     'hemsire',         'gunduz_gece',    TRUE,  FALSE, TRUE,  FALSE, FALSE, FALSE, FALSE, 'Sadece gözlem'),
('Merve Armut',     'hemsire',         'sadece_gunduz',  TRUE,  TRUE,  FALSE, FALSE, FALSE, FALSE, FALSE, 'Sadece triyaj, sadece gündüz.'),
('Murat Sığınç',    'hemsire',         'gunduz_gece',    TRUE,  TRUE,  FALSE, TRUE,  FALSE, FALSE, FALSE, 'Sadece triyaj + ambulans'),
('Ayşe Kartal',     'hemsire',         'sadece_gunduz',  FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE,  'Oryantasyon (21-27 Eylül haftası), gündüz.'),
('Güven Göl',       'hemsire',         'sadece_gunduz',  FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE,  'Oryantasyon (21-27 Eylül haftası), gündüz.');

-- 2) staff
INSERT INTO staff (role_id, full_name, shift_eligibility, note)
SELECT r.id, t.full_name, t.eligibility, t.note
FROM tmp_personel t
JOIN roles r ON r.code = t.role_code
WHERE NOT EXISTS (SELECT 1 FROM staff s WHERE s.full_name = t.full_name);

-- 3) staff_competencies: geniş → uzun
--    "temel" tek sütun ama 3 yetkinliğe açılıyor (IV, IM, HASTA_ILT).
INSERT INTO staff_competencies (staff_id, competency_id)
SELECT s.id, c.id
FROM tmp_personel t
JOIN staff s ON s.full_name = t.full_name
CROSS JOIN LATERAL (VALUES
    ('IV',              t.temel),
    ('IM',              t.temel),
    ('HASTA_ILT',       t.temel),
    ('TRIYAJ',          t.triyaj),
    ('GOZLEM',          t.gozlem),
    ('AMBULANS',        t.ambulans),
    ('SHIFT_YETKILISI', t.ekip_lideri),
    ('SAYIM',           t.sayim)
) AS y (competency_code, has_it)
JOIN competencies c ON c.code = y.competency_code
WHERE y.has_it
ON CONFLICT (staff_id, competency_id) DO NOTHING;

-- 4) Sözleşmeler: hedef boş = kuraldaki 200 saat
INSERT INTO contracts (staff_id, valid_period, monthly_target_hours)
SELECT s.id, daterange('2026-01-01', NULL), NULL
FROM staff s
WHERE NOT EXISTS (SELECT 1 FROM contracts c WHERE c.staff_id = s.id);

-- 5) Oryantasyon: eğitimdekiler → eğitim hemşiresi (Şükran Ünlü)
UPDATE staff
SET is_orientation = TRUE,
    buddy_staff_id = (SELECT id FROM staff WHERE full_name = 'Şükran Ünlü')
WHERE full_name IN (SELECT full_name FROM tmp_personel WHERE oryantasyon);

-- Uyumsuz çift: gerçek veri gelmedi, boş bırakıldı.

COMMIT;
