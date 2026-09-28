-- seeds/020_oryantasyon_gece.sql
-- 28.09.2026: Oryantasyondaki iki kişi gece de çalışabilir.
--
-- Kağıt Eylül çizelgesinde Ayşe Kartal 28-29 Eylül'de GECE(ORY) çalışmış.
-- seeds/007'de ikisi de 'sadece_gunduz' girilmişti; saha bunu yalanlıyor.
-- Acil takviye kuralının (C-022) geceyi de kapsayabilmesi buna bağlı.
UPDATE staff
SET shift_eligibility = 'gunduz_gece'
WHERE full_name IN ('Ayşe Kartal', 'Güven Göl')
  AND shift_eligibility <> 'gunduz_gece';
