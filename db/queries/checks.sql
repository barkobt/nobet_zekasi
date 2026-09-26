-- queries/checks.sql
-- Veritabanı bitti mi? Bu dosyayı bölüm bölüm çalıştır (her bloğu seç, ⌥+X).
-- B ve C bölümleri BEGIN ... ROLLBACK içinde: hiçbir iz bırakmaz.

---------------------------------------------------------------------------
-- A) SAYIM KONTROLLERİ (beklenen değerler yorumda)
---------------------------------------------------------------------------
SELECT 'tablo'       AS ne, count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'  -- 22
UNION ALL SELECT 'view',        count(*) FROM information_schema.views WHERE table_schema = 'public'                               -- 5
UNION ALL SELECT 'personel',    count(*) FROM staff                                                                                -- 19
UNION ALL SELECT 'kişi×yetkinlik', count(*) FROM staff_competencies                                                                -- 92
UNION ALL SELECT 'ihtiyaç satırı', count(*) FROM need_template_rows                                                                -- 10
UNION ALL SELECT 'kural',       count(*) FROM constraints                                                                          -- 18
UNION ALL SELECT 'parametre',   count(*) FROM constraint_params;                                                                   -- 6

-- Yetkinlik matrisi (E-02) sütun toplamları: "triyaj yetkini kaç kişi?"
SELECT c.code, count(sc.staff_id) AS kisi_sayisi
FROM competencies c
LEFT JOIN staff_competencies sc ON sc.competency_id = c.id
GROUP BY c.id, c.code
ORDER BY c.id;

-- İhtiyaç şablonu okunabilir hali
SELECT st.code AS vardiya, ntr.slot_code, ntr.min_count,
       string_agg(c.code, ' + ' ORDER BY c.code) AS gereken_yetkinlik
FROM need_template_rows ntr
JOIN shift_types st ON st.id = ntr.shift_type_id
LEFT JOIN need_template_row_competencies x ON x.need_template_row_id = ntr.id
LEFT JOIN competencies c ON c.id = x.competency_id
GROUP BY st.code, ntr.slot_code, ntr.min_count, ntr.id
ORDER BY st.code DESC, ntr.id;

-- Yol Haritası Adım 4 kontrolü: "Merve Toprak sadece gündüz" bilgisi kaç yerde? → 1 (staff.shift_eligibility)
SELECT full_name, shift_eligibility FROM staff WHERE full_name = 'Merve Toprak';

---------------------------------------------------------------------------
-- B) MİNİ ÇİZELGE DENEMESİ: görünümler çalışıyor mu?
---------------------------------------------------------------------------
BEGIN;

INSERT INTO schedule_drafts (unit_id, month_start, name)
SELECT id, '2026-10-01', 'Deneme' FROM units WHERE code = 'ACIL_SERVIS';

-- Ayşe: 1 ve 2 Ekim gece, Merve: 1 Ekim gündüz
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date)
SELECT d.id, s.id, st.id, x.gun::date
FROM (VALUES ('Ayşe Korkmaz', 'GECE', '2026-10-01'),
             ('Ayşe Korkmaz', 'GECE', '2026-10-02'),
             ('Merve Toprak', 'GUNDUZ', '2026-10-01')) AS x (ad, vardiya, gun)
JOIN staff s        ON s.full_name = x.ad
JOIN shift_types st ON st.code = x.vardiya
JOIN schedule_drafts d ON d.name = 'Deneme';

-- Ayşe'nin 1 Ekim gecesine görev: TRIYAJ + AMBULANS
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT a.id, c.id
FROM assignments a
JOIN staff s ON s.id = a.staff_id AND s.full_name = 'Ayşe Korkmaz'
JOIN competencies c ON c.code IN ('TRIYAJ', 'AMBULANS')
WHERE a.work_date = '2026-10-01';

-- Merve 1 Ekim'de 18:00 yerine 20:00'de çıktı (2 saat geç çıkış mesaisi)
INSERT INTO actual_times (assignment_id, actual_start, actual_end, reason)
SELECT a.id, '2026-10-01 08:30+03', '2026-10-01 20:00+03', 'Yoğunluk, geç çıkış'
FROM assignments a JOIN staff s ON s.id = a.staff_id
WHERE s.full_name = 'Merve Toprak';

SELECT full_name, shift_count, planned_hours, worked_hours, missing_hours, overtime_late_exit
FROM v_monthly_hours WHERE full_name IN ('Ayşe Korkmaz', 'Merve Toprak');
-- Beklenen: Ayşe 2 vardiya, 29 saat. Merve 1 vardiya, plan 9.5, çalışılan 11.5, geç çıkış 2.

SELECT full_name, night_count, night_rank FROM v_fairness ORDER BY night_rank LIMIT 3;
-- Beklenen: Ayşe 2 gece, 1. sırada

SELECT day, shift_code, slot_code, required, assigned
FROM v_daily_coverage WHERE day = '2026-10-01' ORDER BY shift_code, slot_code;
-- Beklenen: GECE GENEL 1/5, GECE TRIYAJ 1/3, GECE AMBULANS 1/2, GUNDUZ GENEL 1/6 ...

ROLLBACK;

---------------------------------------------------------------------------
-- C) KISIT DENEMELERİ: her biri HATA vermeli (hata = kısıt çalışıyor)
--    Her denemeyi AYRI çalıştır. Hata sonrası transaction bozulur, o yüzden her biri kendi BEGIN/ROLLBACK'inde.
---------------------------------------------------------------------------

-- C1) Aynı kişi aynı gün iki vardiya → uq_assignments_draft_staff_date
BEGIN;
INSERT INTO schedule_drafts (unit_id, month_start, name) SELECT id, '2026-10-01', 'T' FROM units;
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date)
SELECT d.id, s.id, st.id, '2026-10-05'
FROM schedule_drafts d, staff s, shift_types st
WHERE d.name = 'T' AND s.full_name = 'Ayşe Korkmaz' AND st.code IN ('GUNDUZ', 'GECE');
ROLLBACK;

-- C2) Aynı ay için iki yayınlanmış taslak → uq_drafts_one_published
BEGIN;
INSERT INTO schedule_drafts (unit_id, month_start, name, status, published_at)
SELECT id, '2026-10-01', x, 'yayinlandi', now() FROM units, (VALUES ('A'), ('B')) v(x);
ROLLBACK;

-- C3) Ayın ilk günü olmayan taslak → ck_drafts_month_start
BEGIN;
INSERT INTO schedule_drafts (unit_id, month_start, name) SELECT id, '2026-10-15', 'X' FROM units;
ROLLBACK;

-- C4) Çıkışı girişten önce gerçekleşen kayıt → ck_actual_end_after_start
--     (önce geçerli bir atama lazım, o yüzden birkaç satır)
BEGIN;
INSERT INTO schedule_drafts (unit_id, month_start, name) SELECT id, '2026-10-01', 'Y' FROM units;
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date)
SELECT d.id, s.id, st.id, '2026-10-01' FROM schedule_drafts d, staff s, shift_types st
WHERE d.name = 'Y' AND s.full_name = 'Merve Toprak' AND st.code = 'GUNDUZ';
INSERT INTO actual_times (assignment_id, actual_start, actual_end)
SELECT id, '2026-10-01 18:00+03', '2026-10-01 08:30+03' FROM assignments;
ROLLBACK;

-- C5) Geçmiş ataması olan personeli silmek → fk_assignments_staff (RESTRICT)
BEGIN;
INSERT INTO schedule_drafts (unit_id, month_start, name) SELECT id, '2026-10-01', 'Z' FROM units;
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date)
SELECT d.id, s.id, st.id, '2026-10-01' FROM schedule_drafts d, staff s, shift_types st
WHERE d.name = 'Z' AND s.full_name = 'Ceren Bilgin' AND st.code = 'GUNDUZ';
DELETE FROM staff WHERE full_name = 'Ceren Bilgin';
ROLLBACK;
-- Doğrusu: UPDATE staff SET is_active = FALSE WHERE full_name = 'Ceren Bilgin';

-- C6) Aynı kişiye çakışan iki izin → ex_absences_no_overlap (EXCLUDE)
BEGIN;
INSERT INTO absences (staff_id, period, absence_type)
SELECT id, p, 'yillik_izin' FROM staff,
       (VALUES (daterange('2026-10-05', '2026-10-10')), (daterange('2026-10-08', '2026-10-12'))) v(p)
WHERE full_name = 'Deniz Aksoy';
ROLLBACK;

---------------------------------------------------------------------------
-- D) ADIM 8 ÖRNEĞİ: indeksi tahminle değil ölçerek ekle
---------------------------------------------------------------------------
-- EXPLAIN ANALYZE SELECT * FROM assignments WHERE draft_id = 1 AND work_date = '2026-10-14';
-- Çıktıda "Index Scan using uq_assignments_draft_staff_date" görüyorsan ek indekse gerek yok.


---------------------------------------------------------------------------
-- E) TRİYAJ / GÖZLEM MODELİ (migration 011)
---------------------------------------------------------------------------

-- E1) Rozetsiz kalan var mı? Kural: sorumlu ve oryantasyon dışında HER çalışan
--     ya triyajda ya gözlemdedir. Bu sorgu boş dönmeli.
--     Satır dönerse: kişinin ne TRIYAJ ne GOZLEM yetkinliği var → kadro sorunu.
SELECT s.full_name, a.work_date,
       CASE WHEN st.crosses_midnight THEN 'GECE' ELSE 'GUNDUZ' END AS vardiya
FROM assignments a
JOIN staff s        ON s.id  = a.staff_id
JOIN roles ro       ON ro.id = s.role_id
JOIN shift_types st ON st.id = a.shift_type_id
WHERE NOT s.is_orientation
  AND ro.code <> 'sorumlu_hemsire'
  AND NOT EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id = t.competency_id
                  WHERE t.assignment_id = a.id AND c.code IN ('TRIYAJ', 'GOZLEM'))
ORDER BY a.work_date, s.full_name;

-- E2) Ambulans çıkınca alan boşalan vardiyalar (C-009 ihlali).
--     Sayaç tam olsa bile ihlal olabilir: ambulansın ikisi de aynı alandan çıkarsa.
SELECT day, shift_code, slot_code, assigned, required, remaining_after_ambulance
FROM v_daily_coverage
WHERE remaining_after_ambulance = 0
ORDER BY day, shift_code DESC, slot_code;

-- E3) Görev ihlalleri: yetkinliği olmayana verilen görev + aynı atamada TRIYAJ ve GOZLEM
SELECT violation_type, count(*) FROM v_task_eligibility_violations GROUP BY 1;
