-- 027_ihtiyac_donemi_geri.sql
-- İhtiyaç döneminin başlangıcını 1 Eylül'den 1 Ağustos'a çeker.
--
-- NEDEN: kağıt Eylül çizelgesi 31 Ağustos Pazartesi'den başlıyor (haftanın ilk
-- günü). need_periods [2026-09-01,) olduğu için 31 Ağustos'un HİÇ ihtiyaç satırı
-- yoktu: o gün ne kapsama asgarisi ne de C-009 kuruluyordu ve solver geceye tek
-- kişi yazıp onu ambulansa çıkarabiliyordu — kontrolcü "triyajda 0/1 kişi kaldı"
-- diye yakaladı.
--
-- Mevcut sayılar DEĞİŞMİYOR; yalnız şablonun geçerli olduğu aralık genişliyor.

BEGIN;

UPDATE need_periods
   SET valid_period = daterange(DATE '2026-08-01', upper(valid_period), '[)')
 WHERE lower(valid_period) = DATE '2026-09-01';

COMMIT;
