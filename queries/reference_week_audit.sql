-- queries/reference_week_audit.sql
-- Elle hazırlanan 21–27 Eylül çizelgesini veritabanındaki kurallarla denetler.
-- Hiçbir şeyi değiştirmez, sadece okur.

-- Ortak filtre: referans taslak + o hafta
-- (her sorguda tekrar yazmamak için CTE'ye koyuyoruz)

-- 1) Vardiya başına kişi ve yetkinlik sayısı
--    Ekip lideri ve sayım "görev" değil "o vardiyada böyle biri var mı?" sorusu olduğu için
--    kişinin yetkinliğine bakıyoruz (assignment_tasks'a değil).
WITH ref AS (
    SELECT a.*, st.code AS shift_code, st.start_time
    FROM assignments a
    JOIN shift_types st     ON st.id = a.shift_type_id
    JOIN schedule_drafts d  ON d.id = a.draft_id
    WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
),
has AS (
    SELECT sc.staff_id, c.code
    FROM staff_competencies sc JOIN competencies c ON c.id = sc.competency_id
)
SELECT
    r.work_date,
    to_char(r.work_date, 'TMDy')                                                        AS gun,
    CASE WHEN r.start_time = '08:30' THEN 'GUNDUZ' ELSE 'GECE' END                      AS vardiya,
    count(*) FILTER (WHERE s.is_orientation = FALSE AND ro.code <> 'sorumlu_hemsire')    AS calisan,
    count(*) FILTER (WHERE ro.code = 'sorumlu_hemsire')                                 AS sorumlu,
    count(*) FILTER (WHERE s.is_orientation)                                            AS oryantasyon,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM has WHERE has.staff_id = r.staff_id AND has.code = 'SHIFT_YETKILISI')) AS ekip_lideri,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM has WHERE has.staff_id = r.staff_id AND has.code = 'SAYIM'))           AS sayim,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id = t.competency_id
                                   WHERE t.assignment_id = r.id AND c.code = 'AMBULANS'))                             AS ambulans,
    count(*) FILTER (WHERE EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id = t.competency_id
                                   WHERE t.assignment_id = r.id AND c.code = 'GOZLEM'))                               AS gozlem
FROM ref r
JOIN staff s  ON s.id = r.staff_id
JOIN roles ro ON ro.id = s.role_id
GROUP BY r.work_date, vardiya
ORDER BY r.work_date, vardiya DESC;

-- 2) Gece kuralları: üst üste 2 geceden sonra ertesi gün boş mu?
--    LAG / LEAD: window function ile "bir önceki / bir sonraki satır"a bakmak.
WITH ref AS (
    SELECT a.staff_id, a.work_date, st.crosses_midnight AS gece
    FROM assignments a
    JOIN shift_types st    ON st.id = a.shift_type_id
    JOIN schedule_drafts d ON d.id = a.draft_id
    WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
),
nights AS (
    SELECT staff_id, work_date,
           LAG(work_date) OVER (PARTITION BY staff_id ORDER BY work_date) AS onceki_gece
    FROM ref WHERE gece
)
SELECT s.full_name,
       n.onceki_gece AS gece_1,
       n.work_date   AS gece_2,
       (SELECT st.code FROM assignments a JOIN shift_types st ON st.id = a.shift_type_id
        JOIN schedule_drafts d ON d.id = a.draft_id
        WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
          AND a.staff_id = n.staff_id AND a.work_date = n.work_date + 1) AS ertesi_gun,
       CASE WHEN EXISTS (SELECT 1 FROM assignments a JOIN schedule_drafts d ON d.id = a.draft_id
                         WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
                           AND a.staff_id = n.staff_id AND a.work_date = n.work_date + 1)
            THEN 'İHLAL' ELSE 'uygun' END AS dinlenme
FROM nights n
JOIN staff s ON s.id = n.staff_id
WHERE n.onceki_gece = n.work_date - 1          -- art arda 2 gece
ORDER BY s.full_name, n.work_date;

-- 3) Haftalık saat: 50 saat referansına göre
SELECT s.full_name,
       count(*)                         AS vardiya,
       sum(st.duration_hours)           AS hafta_saat,
       sum(st.duration_hours) - 50      AS fark_50,
       round(sum(st.duration_hours) * 30 / 7, 0) AS aya_oranla
FROM assignments a
JOIN shift_types st    ON st.id = a.shift_type_id
JOIN schedule_drafts d ON d.id = a.draft_id
JOIN staff s           ON s.id = a.staff_id
WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
GROUP BY s.full_name
ORDER BY hafta_saat DESC;

-- 4) Uygunluk dışı atamalar: sadece gündüz çalışabilen biri geceye yazılmış mı?
SELECT s.full_name, a.work_date, st.code AS vardiya
FROM assignments a
JOIN shift_types st    ON st.id = a.shift_type_id
JOIN schedule_drafts d ON d.id = a.draft_id
JOIN staff s           ON s.id = a.staff_id
WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
  AND s.shift_eligibility = 'sadece_gunduz'
  AND st.crosses_midnight
ORDER BY a.work_date;

-- 5) Gündüz eksikleri (E-09 görünümüyle): gereken 5, atanan kaç?
SELECT day, shift_code, required, assigned, assigned - required AS fark
FROM v_daily_coverage cov
JOIN schedule_drafts d ON d.id = cov.draft_id
WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
  AND cov.slot_code = 'GENEL'
  AND cov.day BETWEEN '2026-09-21' AND '2026-09-27'
ORDER BY day, shift_code DESC;
