-- 021_monthly_hours_ayrilanlar.up.sql
-- v_monthly_hours ayrılan personeli hiç saymıyordu (WHERE s.is_active).
--
-- Kağıt Eylül çizelgesinde Efe Mutlu 10 vardiya (140 saat), Çağla Sarıtaş
-- 6 vardiya (57 saat) çalışmış. Raporlar ekranı adlarını ve gece/hafta sonu
-- sayılarını başka bir sorgudan aldığı için satırları görünüyor ama saatleri
-- 0 yazıyordu: "0 saat · 9 gece" gibi kendi içinde çelişen bir satır.
--
-- Kural, çizelge ekranındakiyle aynı: aktif OLMASA da o taslakta ÇALIŞMIŞSA sayılır.
-- Adalet ve 200 saat karşılaştırmasına girip girmediği ayrı bir karar
-- (bkz. solver/data.py → Personel.adalete_girer); burası yalnızca ölçüyor.

CREATE OR REPLACE VIEW v_monthly_hours AS
WITH min_h AS (
    SELECT p.param_value AS min_hours
    FROM constraint_params p
    JOIN constraints c ON c.id = p.constraint_id
    WHERE c.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours'
)
SELECT d.id AS draft_id,
       lower(d.period) AS period_start,
       upper(d.period) AS period_end,
       s.id AS staff_id,
       s.full_name,
       count(h.assignment_id) AS shift_count,
       COALESCE(sum(h.planned_hours), 0::numeric) AS planned_hours,
       COALESCE(sum(h.worked_hours), 0::numeric) AS worked_hours,
       m.min_hours,
       GREATEST(0::numeric, m.min_hours - COALESCE(sum(h.worked_hours), 0::numeric))
           AS missing_hours,
       GREATEST(0::numeric, COALESCE(sum(h.worked_hours), 0::numeric) - m.min_hours)
           AS overtime_monthly,
       COALESCE(sum(h.late_exit_hours), 0::numeric) AS overtime_late_exit,
       GREATEST(
           GREATEST(0::numeric, COALESCE(sum(h.worked_hours), 0::numeric) - m.min_hours),
           COALESCE(sum(h.late_exit_hours), 0::numeric)
       ) AS overtime_max
FROM schedule_drafts d
CROSS JOIN staff s
CROSS JOIN min_h m
LEFT JOIN v_assignment_hours h
       ON h.draft_id = d.id AND h.staff_id = s.id AND d.period @> h.work_date
WHERE s.is_active
   OR EXISTS (SELECT 1 FROM assignments a
               WHERE a.staff_id = s.id AND a.draft_id = d.id)
GROUP BY d.id, d.period, s.id, s.full_name, m.min_hours;
