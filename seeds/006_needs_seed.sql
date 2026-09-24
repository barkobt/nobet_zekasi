-- seeds/006_needs_seed.sql
-- Standart hafta ihtiyaç şablonu.
--
-- KALIP: "Ham veriyi VALUES ile küçük bir sanal tabloya koy, sonra gerçek id'lerle JOIN'le."
--   İnsan kodla düşünür (GECE, TRIYAJ); tablo id ister (7, 12).
--   JOIN, kodu id'ye çeviren sözlüktür. Hiçbir yerde elle id yazmıyoruz.

-- 1) Şablon başlığı
INSERT INTO need_templates (code, name)
VALUES ('standart', 'Standart Hafta')
ON CONFLICT (code) DO NOTHING;

-- 2) Şablon satırları: 2 vardiya × 5 slot = 10 satır, TEK INSERT ile.
--    raw: elle yazdığımız okunabilir tablo (vardiya kodu, slot, kişi sayısı)
--    JOIN shift_types: 'GECE' metnini gerçek shift_type id'sine çevirir
--    JOIN units: aynı kodlu vardiya başka birimde de olabilir; ACIL_SERVIS'inkini seç
--    JOIN need_templates: 'standart' şablonunun id'sini getirir
WITH raw (shift_code, slot_code, min_count, note) AS (
    VALUES
        ('GUNDUZ', 'GENEL',           6, 'Genel mevcut (1''i sadece sorumlu)'),
        ('GUNDUZ', 'SHIFT_YETKILISI', 1, 'En az 1 shift yetkilisi'),
        ('GUNDUZ', 'TRIYAJ',          3, 'Triyaj havuzu (ambulans da bu havuzdan çıkar)'),
        ('GUNDUZ', 'AMBULANS',        2, 'Triyaj havuzunun çoklu görevi'),
        ('GUNDUZ', 'GOZLEM',          2, 'Triyaj havuzundan ayrık'),
        ('GECE',   'GENEL',           5, 'Genel mevcut, sorumlu yok'),
        ('GECE',   'SHIFT_YETKILISI', 1, 'En az 1 shift yetkilisi'),
        ('GECE',   'TRIYAJ',          3, 'Triyaj havuzu (ambulans da bu havuzdan çıkar)'),
        ('GECE',   'AMBULANS',        2, 'Triyaj havuzunun çoklu görevi'),
        ('GECE',   'GOZLEM',          2, 'Triyaj havuzundan ayrık')
)
INSERT INTO need_template_rows (need_template_id, shift_type_id, slot_code, min_count, note)
SELECT nt.id, st.id, raw.slot_code, raw.min_count, raw.note
FROM raw
JOIN units u           ON u.code = 'ACIL_SERVIS'
JOIN shift_types st    ON st.unit_id = u.id AND st.code = raw.shift_code
JOIN need_templates nt ON nt.code = 'standart'
ON CONFLICT (need_template_id, shift_type_id, slot_code) DO NOTHING;

-- 3) Hangi slot hangi yetkinliği ister (köprü tablo).
--    TRIYAJ slotu İKİ yetkinlik ister → raw'da iki satır.
--    GENEL slotunun burada satırı yok → "yetkinlik şartı yok".
--    Bu eşleme her iki vardiyadaki aynı slot'a uygulanır (JOIN slot_code üzerinden).
WITH raw (slot_code, competency_code) AS (
    VALUES
        ('SHIFT_YETKILISI', 'SHIFT_YETKILISI'),
        ('TRIYAJ',          'TRIYAJ'),
        ('TRIYAJ',          'HASTA_ILT'),
        ('AMBULANS',        'AMBULANS'),
        ('GOZLEM',          'GOZLEM')
)
INSERT INTO need_template_row_competencies (need_template_row_id, competency_id)
SELECT ntr.id, c.id
FROM raw
JOIN need_templates nt     ON nt.code = 'standart'
JOIN need_template_rows ntr ON ntr.need_template_id = nt.id AND ntr.slot_code = raw.slot_code
JOIN competencies c         ON c.code = raw.competency_code
ON CONFLICT (need_template_row_id, competency_id) DO NOTHING;

-- 4) Standart şablon 1 Eylül 2026'dan itibaren, bitişi açık.
--    ON CONFLICT DO NOTHING (hedefsiz): EXCLUDE kısıtına takılırsa (zaten kayıt varsa) atla.
INSERT INTO need_periods (unit_id, need_template_id, valid_period)
SELECT u.id, nt.id, daterange('2026-09-01', NULL)
FROM units u
JOIN need_templates nt ON nt.code = 'standart'
WHERE u.code = 'ACIL_SERVIS'
ON CONFLICT DO NOTHING;
