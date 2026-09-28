-- seeds/013_absence_reduction_param.sql
-- 27.09.2026: İzin/rapor günü aylık hedeften kaç saat düşürür (C-004'ün açık sorusu).
--
-- Kataloğun "Bilinen açık sorular" bölümü bunu boş bırakmıştı. Solver bir sayı
-- olmadan çalışamaz; 7,5 saat GEÇİCİ bir değer olarak konuyor ve kodda DEĞİL
-- burada duruyor — hastane teyit edince tek satır UPDATE ile değişir, solver
-- kodu değişmez.
--
-- Neden 7,5: haftalık 5 günlük 37,5 saatlik çalışmanın gün karşılığı. Gündüz
-- vardiyası 9,5 saat olduğu için bir izin günü tam bir vardiyayı silmez.
--
-- Tekrar çalıştırılabilir: ON CONFLICT ile aynı anahtar ikinci kez eklenmez,
-- açıklama yine güncellenir.
INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT id, 'absence_daily_reduction_hours', 7.5,
       'İzin/rapor günü başına aylık hedeften düşülen saat. GEÇİCİ, hastane teyidi bekliyor.'
FROM constraints WHERE code = 'monthly_min_hours'
ON CONFLICT (constraint_id, param_key) DO UPDATE
   SET description = EXCLUDED.description;
