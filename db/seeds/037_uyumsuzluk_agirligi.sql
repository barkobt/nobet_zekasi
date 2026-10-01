-- seeds/037_uyumsuzluk_agirligi.sql
-- C-013 Uyumsuz personel artık solver'da (01.10). ESNEK (Baran): kadro yetmezse
-- yan yana gelebilirler, bedeli ağırlık kadar ve teşhiste görünür.
--
-- Ağırlık 40 → 22.000: 40, karşılanamayan bir isteğin cezasının (O-006, 22.000)
-- yanında hiç etkisi olmayan bir değerdi. Uyumsuzluk en az bir istek kadar ciddi.
-- Kapsama eksiğinin (2.000.000) çok altında: vardiyayı boş bırakmaktansa
-- uyumsuzları yan yana koyar.
--
-- Yalnız varsayılan değerdeyse günceller (E-03'ten elle değiştirilmişse dokunmaz).

UPDATE constraints
   SET default_weight = 22000,
       description = 'Uyumsuz olarak işaretlenen iki personel aynı gün aynı vardiyaya '
                     'yazılmaz. Esnek: kadro yetmezse yan yana gelebilirler, teşhiste görünür.'
 WHERE code = 'incompatible_staff_penalty' AND default_weight = 40;
