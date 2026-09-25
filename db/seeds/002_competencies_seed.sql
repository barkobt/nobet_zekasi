-- seeds/002_competencies_seed.sql
-- kind (migration 010): TASK = vardiya içinde atanan görev, rozeti assignment_tasks'ta durur.
--                       QUALIFICATION = kişinin taşıdığı yetki, staff_competencies'ten okunur.
-- Sınıflandırma burada duruyor çünkü kind bir YETKİNLİK özelliğidir ve seeds/009'un
-- görev rozetlerini yazabilmesi için bu dosyadan önce doğru olması gerekir.
INSERT INTO competencies (code, name, description, kind) VALUES
    ('IV',              'IV kateterizasyon / damar yolu', 'Tek yetkinlik (eski "damar yolu" ile birleşti)', 'QUALIFICATION'),
    ('IM',              'İM enjeksiyon',                  NULL,                                            'QUALIFICATION'),
    ('HASTA_ILT',       'Hasta iletişimi',                'Triyaj ve karşılamada gerekli',                 'QUALIFICATION'),
    ('SHIFT_YETKILISI', 'Shift yetkilisi',                'Vardiya devri ve ekip liderliği (eski adı "sayım yetkilisi")', 'QUALIFICATION'),
    ('TRIYAJ',          'Triyaj',                         'Gözlem havuzundan ayrık çalışır',               'TASK'),
    ('AMBULANS',        'Ambulans görevi',                NULL,                                            'TASK'),
    ('GOZLEM',          'Gözlem alanı',                   'Triyaj havuzundan ayrık çalışır',               'TASK')
ON CONFLICT (code) DO NOTHING;

-- Daha önce kurulmuş bir veritabanında satırlar zaten vardır; ON CONFLICT DO NOTHING
-- onları güncellemez. Sınıflandırmayı ayrıca uygula (tekrar çalıştırılabilir kalsın).
UPDATE competencies SET kind = 'TASK'
WHERE code IN ('TRIYAJ', 'AMBULANS', 'GOZLEM') AND kind <> 'TASK';

UPDATE competencies SET kind = 'QUALIFICATION'
WHERE code NOT IN ('TRIYAJ', 'AMBULANS', 'GOZLEM') AND kind <> 'QUALIFICATION';
