-- seeds/005_roles_seed.sql
INSERT INTO roles (code, name) VALUES
    ('sorumlu_hemsire', 'Sorumlu Hemşire'),
    ('shift_yetkilisi', 'Ekip Lideri (Shift Yetkilisi)'),
    ('hemsire',         'Hemşire'),
    ('att_paramedik',   'ATT / Paramedik')
ON CONFLICT (code) DO NOTHING;
