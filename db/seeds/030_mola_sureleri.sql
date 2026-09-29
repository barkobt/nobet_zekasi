-- 030_mola_sureleri.sql
-- Vardiya başına mola süreleri (Edem, 29.09.2026).
--
-- GUNDUZ  80 dk  (1 sa 20 dk) → net 8 sa 10 dk = 490 dk
-- GECE   210 dk  (3 sa 30 dk) → net 11 sa      = 660 dk
--
-- GUNDUZ_CMT (sorumlu hemşirenin 5,5 saatlik kısa Cumartesisi) 0 BIRAKILDI:
-- Edem yalnız tam gündüz ve gece için süre verdi. 5,5 saatlik bir vardiyaya
-- 80 dk mola yazmak bizim uydurmamız olurdu ve sorumlu hemşirenin saatini
-- haksız yere düşürürdü. Doğru değer öğrenilince E-01'den girilir, deploy
-- gerekmez. ** HASTANEYE SORULACAK **
--
-- Pasif vardiyalar (24 saatlikler, kısa gece) 0: kullanılmıyorlar.
--
-- Tekrar çalıştırılabilir: koşulsuz UPDATE, koda göre.

UPDATE shift_types SET break_minutes =  80 WHERE code = 'GUNDUZ';
UPDATE shift_types SET break_minutes = 210 WHERE code = 'GECE';
