-- Eski hali: yalnız aktif personel.
CREATE OR REPLACE VIEW v_monthly_hours AS
WITH min_h AS (
    SELECT p.param_value AS min_hours
    FROM constraint_params p
    JOIN constraints c ON c.id = p.constraint_id
    WHERE c.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours'
)
SELECT d.id AS draft_id, lower(d.period) AS period_start, upper(d.period) AS period_end,
       s.id AS staff_id, s.full_name,
       count(h.assignment_id) AS shift_count,
       COALESCE(sum(h.planned_hours), 0::numeric) AS planned_hours,
       COALESCE(sum(h.worked_hours), 0::numeric) AS worked_hours,
       m.min_hours,
       GREATEST(0::numeric, m.min_hours - COALESCE(sum(h.worked_hours), 0::numeric)) AS missing_hours,
       GREATEST(0::numeric, COALESCE(sum(h.worked_hours), 0::numeric) - m.min_hours) AS overtime_monthly,
       COALESCE(sum(h.late_exit_hours), 0::numeric) AS overtime_late_exit,
       GREATEST(GREATEST(0::numeric, COALESCE(sum(h.worked_hours), 0::numeric) - m.min_hours),
                COALESCE(sum(h.late_exit_hours), 0::numeric)) AS overtime_max
FROM schedule_drafts d
CROSS JOIN staff s
CROSS JOIN min_h m
LEFT JOIN v_assignment_hours h ON h.draft_id = d.id AND h.staff_id = s.id AND d.period @> h.work_date
WHERE s.is_active
GROUP BY d.id, d.period, s.id, s.full_name, m.min_hours;
