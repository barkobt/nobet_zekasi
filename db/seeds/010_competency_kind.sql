-- seeds/010_competency_kind.sql
-- Migration 010'un açtığı üç alanın VERİSİ. Tekrar çalıştırılabilir (hepsi UPDATE).

BEGIN;

-- 1) Yetkinlik sınıflandırması (kind) migration 010'da yapılır — trigger ona bağlı
--    ve seeds/009 bu dosyadan önce çalışıyor. Ayrıntı migration dosyasının A1 notunda.

-- 2) Katalog kodları (docs/kisit-katalogu.md).
--    KALIP: ham eşleme VALUES ile, JOIN kodu id'ye çevirir — hiçbir yerde elle id yok.
--    count_authority_required kataloğa 24.09'da sonradan eklendi, karşılığı yok → NULL kalır.
UPDATE constraints c
SET catalog_code = m.catalog_code
FROM (VALUES
    ('consecutive_nights_limit',    'C-002'),
    ('weekly_reference_hours',      'C-003'),
    ('monthly_min_hours',           'C-004'),
    ('day_shift_min_crew',          'C-005'),
    ('night_shift_min_crew',        'C-006'),
    ('shift_lead_required',         'C-007'),
    ('responsible_nurse_schedule',  'C-008'),
    ('ambulance_observation_limit', 'C-009'),
    ('observation_pool_separate',   'C-010'),
    ('triage_pool_min_size',        'C-011'),
    ('incompatible_staff_penalty',  'C-013'),
    ('rest_after_two_nights',       'C-014'),
    ('weekly_rest_event_required',  'C-016'),
    ('day_only_staff_restriction',  'C-017'),
    ('tasks_within_shift_crew',     'C-019'),
    ('orientation_buddy_required',  'C-020'),
    ('overtime_minimization',       'O-001'),
    ('fairness_balance',            'O-002')
) AS m (code, catalog_code)
WHERE c.code = m.code
  AND c.catalog_code IS DISTINCT FROM m.catalog_code;

-- 3) İhtiyaç satırı → kural bağı.
--    GENEL satırı vardiyaya göre farklı kurala bağlanır (gündüz/gece asgari mevcut),
--    diğer slotlar her iki vardiyada aynı kurala bağlanır → shift_code NULL = "ikisi de".
UPDATE need_template_rows ntr
SET constraint_id = c.id
FROM (VALUES
    ('GENEL',           'GUNDUZ', 'day_shift_min_crew'),
    ('GENEL',           'GECE',   'night_shift_min_crew'),
    ('SHIFT_YETKILISI', NULL,     'shift_lead_required'),
    ('SAYIM',           NULL,     'count_authority_required'),
    ('TRIYAJ',          NULL,     'triage_pool_min_size'),
    ('AMBULANS',        NULL,     'ambulance_observation_limit'),
    ('GOZLEM',          NULL,     'observation_pool_separate')
) AS m (slot_code, shift_code, constraint_code)
JOIN constraints c ON c.code = m.constraint_code
WHERE ntr.slot_code = m.slot_code
  AND (m.shift_code IS NULL
       OR EXISTS (SELECT 1 FROM shift_types st
                  WHERE st.id = ntr.shift_type_id AND st.code = m.shift_code))
  AND ntr.constraint_id IS DISTINCT FROM c.id;

COMMIT;
