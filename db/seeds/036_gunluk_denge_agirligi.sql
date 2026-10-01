-- seeds/036_gunluk_denge_agirligi.sql
-- O-009 Günlük mevcut dengesi ağırlığı 2.000 → 20.000 (Baran, 01.10.2026).
--
-- "Gündüzü 10'a çıkan günler var ama hafta sonu 5-5-5-5; ortalama birbirine
-- yakın olsun." 2.000'de denge cezası (gün başına 1 kişi fark = 60.000, model
-- ölçeğinde) hafta sonu adaletinin uç farkı cezasının (1,26 milyon) yanında
-- sönük kalıyordu. Ölçüm (01.10, 120 sn): 20.000'de Ekim'in solver günlerinde
-- gündüz 6–9, gece 5; hafta içi / hafta sonu ortalaması 7,3 / 7,0.
-- Kapsama eksiğinin (2.000.000) çok altında kalır: denge kapsamanın önüne geçmez.
--
-- Yalnız varsayılan değerdeyse günceller: E-03'ten elle değiştirilmiş ağırlığa
-- dokunmaz. Tekrar çalıştırılabilir.

UPDATE constraints
   SET default_weight = 20000
 WHERE code = 'daily_crew_balance' AND default_weight = 2000;
