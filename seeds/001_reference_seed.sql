-- seeds/001_reference_seed.sql

INSERT INTO units (code, name)
VALUES ('ACIL_SERVIS', 'Erişkin Acil Servis')
ON CONFLICT (code) DO NOTHING;

INSERT INTO shift_types (unit_id, code, name, start_time, duration_hours)
SELECT id, 'GUNDUZ', 'Gündüz', '08:30', 9.5
FROM units WHERE code = 'ACIL_SERVIS'
ON CONFLICT (unit_id, code) DO NOTHING;

INSERT INTO shift_types (unit_id, code, name, start_time, duration_hours)
SELECT id, 'GECE', 'Gece', '18:00', 14.5
FROM units WHERE code = 'ACIL_SERVIS'
ON CONFLICT (unit_id, code) DO NOTHING;


