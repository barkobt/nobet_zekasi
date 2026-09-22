-- seeds/004_constraint_params_seed.sql

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'max_consecutive_nights', 2, 'Üst üste çalışılabilecek en fazla gece sayısı'
FROM constraints WHERE code = 'consecutive_nights_limit'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'monthly_min_hours', 200, 'Kişi başına aylık asgari saat'
FROM constraints WHERE code = 'monthly_min_hours'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'weekly_reference_hours', 50, 'Haftalık referans saat (soft)'
FROM constraints WHERE code = 'weekly_reference_hours'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'rest_trigger_nights', 2, 'Kaç gece sonrası boşluk tetiklenir'
FROM constraints WHERE code = 'rest_after_two_nights'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'rest_gap_hours', 24, 'Zorunlu boşluğun süresi (saat)'
FROM constraints WHERE code = 'rest_after_two_nights'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'weekly_min_rest_events', 1, 'Haftada en az kaç dinlenme olayı gerekir'
FROM constraints WHERE code = 'weekly_rest_event_required'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

