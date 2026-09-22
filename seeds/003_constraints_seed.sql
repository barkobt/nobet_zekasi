-- seeds/003_constraints_seed.sql

INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source) VALUES
    ('consecutive_nights_limit',   'Ardışık gece sınırı',              'Üst üste en fazla 2 gece çalışılabilir', TRUE, NULL, 'kisi',    'belirsiz'),
    ('monthly_min_hours',          'Aylık asgari saat',                'Kişi başına aylık en az 200 saat, katı alt sınır', TRUE, NULL, 'ay',      'kurumsal'),
    ('day_shift_min_crew',         'Gündüz asgari mevcut',             'Gündüz vardiyasında en az 6 kişi bulunur (sayı need_template_rows''ta)', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('night_shift_min_crew',       'Gece asgari mevcut',               'Gece vardiyasında en az 5 kişi bulunur, sorumlu yoktur', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('shift_lead_required',        'Shift yetkilisi zorunluluğu',      'Her vardiyada en az 1 shift yetkilisi bulunmalı', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('responsible_nurse_schedule', 'Sorumlu hemşire programı',         'Hafta içi gündüz, Cumartesi 08:30-14:00, Pazar izinli', TRUE, NULL, 'hafta',   'kurumsal'),
    ('ambulance_from_triage_pool', 'Ambulans triyaj havuzundan',       'Ambulans görevi triyaj havuzundaki kişilerce karşılanır, ayrı kadro değil', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('observation_pool_separate',  'Gözlem havuzu ayrık',              'Gözlem alanında 2 kişi, triyaj görevindekilerden farklı olmalı', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('triage_pool_min_size',       'Triyaj havuzu asgari boyutu',      'Triyajda en az 3 yetkin kişi, ambulansı da bu havuz karşılar', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('rest_after_two_nights',      '2 gece sonrası yasal boşluk',      '2 gece art arda çalışıldıysa 24 saat yasal boşluk zorunlu', TRUE, NULL, 'kisi',    'kurumsal'),
    ('weekly_rest_event_required', 'Haftalık dinlenme şartı',          'Haftada en az 1 dinlenme olayı: izin günü VEYA 2 gece sonrası boşluk', TRUE, NULL, 'hafta',   'yasal'),
    ('day_only_staff_restriction', 'Sadece gündüz kısıtı',             'Sadece gündüz çalışabilen personel geceye yazılamaz', TRUE, NULL, 'kisi',    'kurumsal'),
    ('tasks_within_shift_crew',    'Görevler vardiya mevcudu içinden', 'Ambulans/gözlem görevleri vardiya mevcudunun içinden atanır, ek kadro değil', TRUE, NULL, 'vardiya', 'kurumsal'),
    ('orientation_buddy_required', 'Oryantasyon eşleştirmesi',         'Oryantasyondaki personel eğitim hemşiresiyle birebir çalışır', TRUE, NULL, 'kisi',    'kurumsal'),

    ('weekly_reference_hours',     'Haftalık referans süre',           'Haftalık 50 saat referans değer, sapma cezalandırılır ama yasaklanmaz', FALSE, 10,  'hafta', 'kurumsal'),
    ('incompatible_staff_penalty', 'Uyumsuz kişi cezası',              'Uyumsuz kişiler aynı vardiyaya yazılırsa ceza puanı uygulanır', FALSE, 40,  'vardiya', 'kurumsal'),
    ('overtime_minimization',      'Fazla mesai minimizasyonu',        'Amaç: aylık 200 saat üzeri fazla mesai toplamı minimize edilir', FALSE, 200, 'ay', 'kurumsal'),
    ('fairness_balance',           'Adil dağılım',                     'Amaç: kişiler arası saat dağılımı dengeli olmalı (max-min farkı minimize)', FALSE, 220, 'ay', 'kurumsal')
ON CONFLICT (code) DO NOTHING;


