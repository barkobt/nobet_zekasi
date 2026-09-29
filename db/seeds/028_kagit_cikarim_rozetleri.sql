-- 028_kagit_cikarim_rozetleri.sql
-- Kağıt Eylül'de BİZİM ÇIKARIMIMIZLA eklenen TRIYAJ rozetlerini kaldırır.
--
-- NEDEN: kağıtta görev rengi yoksa "triyaj" varsaymıştık. Eda Karakuş (4 gün) ve
-- Derya Torun (4 gün) TRIYAJ yetkinliğine sahip değil, bu yüzden kontrolcü
-- "rozeti var ama yetkinliği yok" diyordu. İhlal kağıdın değil, bizim
-- varsayımımızın ürünü — kağıdı olduğundan kötü gösteriyordu.
--
-- Rozet GOZLEM'e ÇEVRİLMİYOR: o da bir başka varsayım olurdu. Satır rozetsiz
-- bırakılıyor, anlamı "kağıtta görev belirtilmemiş". Kontrolcü referans
-- kaynaklı rozetsiz satırları D-4'te saymıyor (solver/validate.py).
--
-- Pembe işaretli AMBULANS rozetlerine DOKUNULMUYOR: onlar kağıtta gerçekten
-- işaretli. Muhammet Edem ve Zehra Kutucu'nun ambulans yetkisi hastaneye
-- soruldu; cevap gelene kadar yetkinlikler değişmiyor, ihlal olarak duruyor.

BEGIN;

DELETE FROM assignment_tasks t
USING assignments a, staff s, competencies c, schedule_drafts d
WHERE t.assignment_id = a.id
  AND a.staff_id = s.id
  AND t.competency_id = c.id
  AND a.draft_id = d.id
  AND d.name = 'Eylül 2026 (kağıt)'
  AND c.code = 'TRIYAJ'
  AND s.full_name IN ('Eda Karakuş', 'Derya Torun')
  -- Yalnız yetkinliği OLMAYANI sil: ileride yetkinlik eklenirse bu seed
  -- tekrar çalıştırıldığında doğru rozeti silmesin.
  AND NOT EXISTS (
        SELECT 1 FROM staff_competencies sc
         WHERE sc.staff_id = s.id AND sc.competency_id = c.id
      );

COMMIT;
