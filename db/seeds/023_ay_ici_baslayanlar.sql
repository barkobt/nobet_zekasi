-- 023_ay_ici_baslayanlar.sql
-- Eylül'de ay içinde işe başlayan üç kişinin sözleşme başlangıcı.
--
-- NEDEN: hastane kararı — "ayrılan personel ve ay içinde sonradan başlayanlar
-- (Serpil, Ayşe, Güven) KAPSAMA sayımına girer, ama saat/gece adaleti ve 200 saat
-- hesaplarına GİRMEZ." Bu ayrımı solver sözleşme aralığından çıkarıyor
-- (solver/data.py → Personel.adalete_girer): sözleşmesi dönemin tamamını
-- kapsamayan kişi adalet havuzunun dışında kalır.
--
-- Tarihler kağıt çizelgeden okundu; üçünün de ilk çalıştığı gün bir PAZARTESİ:
--   Serpil Demir  → 7 Eylül 2026
--   Ayşe Kartal   → 14 Eylül 2026
--   Güven Göl     → 21 Eylül 2026
-- Sözleşmeler AÇIK UÇLU kalır (üst sınır yok): üçü de çalışmaya devam ediyor,
-- bu yüzden Ekim ve Kasım'da adalet havuzunun İÇİNDEDİR.
--
-- Tekrar çalıştırılabilir: valid_period'u mutlak değere set eder.

BEGIN;

UPDATE contracts c
   SET valid_period = daterange(v.bas, upper(c.valid_period), '[)')
  FROM (VALUES
          ('Serpil Demir', DATE '2026-09-07'),
          ('Ayşe Kartal',  DATE '2026-09-14'),
          ('Güven Göl',    DATE '2026-09-21')
       ) AS v(ad, bas)
  JOIN staff s ON s.full_name = v.ad
 WHERE c.staff_id = s.id
   AND lower(c.valid_period) <> v.bas;

COMMIT;
