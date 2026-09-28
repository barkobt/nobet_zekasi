-- seeds/021_kagit_eylul_kadro.sql
-- 28.09.2026: Kağıt Eylül çizelgesinin gerektirdiği referans veri.
--
-- 1) KISA GECE VARDİYASI — GECE_0100
--    Kağıtta "GECE(01:00)" olarak 7 kez geçiyor (21-29 Eylül). 18:00-01:00, 7 saat.
--    PASİF: solver bunu kullanmaz (data.py yalnız is_active vardiyaları okur),
--    yalnız geçmiş kayıtların doğru yazılabilmesi için var.
--    Not: crosses_midnight üretilmiş kolon — 18:00 + 7 sa = 01:00 → TRUE.
INSERT INTO shift_types (unit_id, code, name, start_time, duration_hours, is_active)
SELECT id, 'GECE_0100', 'Kısa gece (18:00-01:00)', '18:00', 7, FALSE
FROM units WHERE code = 'ACIL_SERVIS'
ON CONFLICT (unit_id, code) DO NOTHING;

-- 2) AYRILAN PERSONEL
--    Kağıtta var, bugünkü kadroda yok. is_active = FALSE:
--    personel listesinde ve solver'da görünmezler, geçmiş kayıtlarda sayılırlar.
--    (assignments.staff_id FK'si RESTRICT olduğu için zaten silinemezler.)
INSERT INTO staff (role_id, full_name, shift_eligibility, is_active, note)
SELECT r.id, x.ad, x.tip, FALSE, x.notu
FROM (VALUES
    ('Efe Mutlu',     'hemsire', 'gunduz_gece',
     'Ayrılmış personel. Kağıt Eylül çizelgesinde 31.08-20.09 arasında çalışmış.'),
    ('Çağla Sarıtaş', 'hemsire', 'sadece_gunduz',
     'Ayrılmış personel. Kağıt Eylül çizelgesinde 31.08-06.09 arasında oryantasyonda.')
) AS x (ad, rol, tip, notu)
JOIN roles r ON r.code = x.rol
WHERE NOT EXISTS (SELECT 1 FROM staff s WHERE s.full_name = x.ad);

--    Çağla oryantasyondaydı; şema oryantasyon için eş zorunlu kılıyor
--    (ck_staff_orientation_buddy). Eğitim hemşiresi Şükran Ünlü.
UPDATE staff
SET is_orientation = TRUE,
    buddy_staff_id = (SELECT id FROM staff WHERE full_name = 'Şükran Ünlü')
WHERE full_name = 'Çağla Sarıtaş' AND NOT is_orientation;

-- 3) EFE MUTLU'NUN YETKİNLİKLERİ
--    Kağıttan okundu: 8 triyaj, 2 gözlem, hiç ambulans yok.
--    Temel yetkinlikler (IV, İM, hasta iletişimi) diğer hemşirelerle aynı varsayıldı.
--    Çağla Sarıtaş oryantasyonda olduğu için yetkinliği yok (Ayşe/Güven gibi).
INSERT INTO staff_competencies (staff_id, competency_id)
SELECT s.id, c.id
FROM staff s
CROSS JOIN competencies c
WHERE s.full_name = 'Efe Mutlu'
  AND c.code IN ('IV', 'IM', 'HASTA_ILT', 'TRIYAJ', 'GOZLEM')
ON CONFLICT (staff_id, competency_id) DO NOTHING;

-- 4) Sözleşme — AÇIK UÇLU DEĞİL: ayrıldıkları gün biter. Böylece raporlar
--    onları ayrıldıktan sonraki dönemlerde hedefli personel saymaz.
INSERT INTO contracts (staff_id, valid_period, monthly_target_hours, note)
SELECT s.id, x.aralik::daterange, NULL, 'Ayrılış tarihi kağıt çizelgeden'
FROM (VALUES
    ('Efe Mutlu',     '[2026-01-01,2026-09-21)'),
    ('Çağla Sarıtaş', '[2026-01-01,2026-09-07)')
) AS x (ad, aralik)
JOIN staff s ON s.full_name = x.ad
WHERE NOT EXISTS (SELECT 1 FROM contracts c WHERE c.staff_id = s.id);
