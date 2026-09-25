-- seeds/002_competencies_seed.sql
INSERT INTO competencies (code, name, description) VALUES
    ('IV',              'IV kateterizasyon / damar yolu', 'Tek yetkinlik (eski "damar yolu" ile birleşti)'),
    ('IM',              'İM enjeksiyon',                  NULL),
    ('HASTA_ILT',       'Hasta iletişimi',                'Triyaj ve karşılamada gerekli'),
    ('SHIFT_YETKILISI', 'Shift yetkilisi',                'Vardiya devri ve ekip liderliği (eski adı "sayım yetkilisi")'),
    ('TRIYAJ',          'Triyaj',                         'Gözlem havuzundan ayrık çalışır'),
    ('AMBULANS',        'Ambulans görevi',                NULL),
    ('GOZLEM',          'Gözlem alanı',                   'Triyaj havuzundan ayrık çalışır')
ON CONFLICT (code) DO NOTHING;
