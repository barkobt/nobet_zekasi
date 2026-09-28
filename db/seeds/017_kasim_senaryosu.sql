-- seeds/017_kasim_senaryosu.sql
-- 28.09.2026: Sunum için "eksik açıklamaları" senaryosu.
--
-- AMAÇ: E-10'un dolu göründüğü hazır bir taslak. Ekim çizelgesi TEMİZ kalır;
-- izinler Kasım'a konur, Ekim'in çözümüne dokunulmaz.
--
-- Senaryo: gece çalışabilen 10 triyaj yetkilisinin 6'sı 9-15 Kasım haftasında
-- yok. Havuz 4'e iner, gece triyaj 3 kişi ister → eksik kaçınılmaz.
-- Ayrıca 3 "mümkünse" tercihi: karşılanamayanlar E-10'da O-006 altında görünür.
--
-- TEKRAR ÇALIŞTIRILABİLİR: taslak adla aranır (yoksa açılır), izinler ve
-- tercihler NOT EXISTS ile korunur. İkinci çalıştırma hiçbir şeyi çoğaltmaz
-- ve çözülmüş atamaları SİLMEZ.
--
-- NOT: taslak burada yalnız OLUŞTURULUR, çözülmez. Çözmek E-08'den "Çöz"
-- düğmesiyle yapılır — canlıda gerçek solver'ın çalıştığı da böyle görülür.

BEGIN;

-- 1) Taslak
INSERT INTO schedule_drafts (unit_id, period, name)
SELECT u.id, daterange('2026-11-01', '2026-12-01', '[)'), 'Kasım 2026 — izin senaryosu'
FROM units u
WHERE u.code = 'ACIL_SERVIS'
  AND NOT EXISTS (SELECT 1 FROM schedule_drafts d WHERE d.name = 'Kasım 2026 — izin senaryosu');

-- 2) İzinler — 9-15 Kasım (üst sınır dışlayıcı: 16 Kasım'a kadar)
--    absences'ta kişi başına çakışmayan aralık kısıtı (EXCLUDE) var; o yüzden
--    aynı kişiye çakışan bir izin zaten varsa bu satır atlanır.
INSERT INTO absences (staff_id, period, absence_type, note)
SELECT s.id, daterange('2026-11-09', '2026-11-16', '[)'), x.tur, 'Senaryo: 9-15 Kasım toplu yokluk'
FROM (VALUES
    ('Birol Karaca',  'yillik_izin'),
    ('Emre Baydilli', 'yillik_izin'),
    ('Kader Can',     'yillik_izin'),
    ('Murat Sığınç',  'yillik_izin'),
    ('Muhammet Edem', 'rapor'),
    ('Zehra Kutucu',  'rapor')
) AS x (ad, tur)
JOIN staff s ON s.full_name = x.ad
WHERE NOT EXISTS (
    SELECT 1 FROM absences a
    WHERE a.staff_id = s.id AND a.period && daterange('2026-11-09', '2026-11-16', '[)')
);

-- 3) "Mümkünse" tercihleri — karşılanamayanlar E-10'da O-006 altında çıkar
INSERT INTO availability_rules (staff_id, target_date, rule_type, status, note)
SELECT s.id, x.gun::date, x.tur, 'MUMKUNSE', 'Senaryo: karşılanamayan tercih örneği'
FROM (VALUES
    ('Engin Sümer',  '2026-11-11', 'BOS_GUN'),
    ('Fatih Sırcan', '2026-11-12', 'BOS_GUN'),
    ('Sıla Öner',    '2026-11-13', 'SADECE_GUNDUZ')
) AS x (ad, gun, tur)
JOIN staff s ON s.full_name = x.ad
ON CONFLICT (staff_id, target_date, rule_type) DO NOTHING;

COMMIT;
