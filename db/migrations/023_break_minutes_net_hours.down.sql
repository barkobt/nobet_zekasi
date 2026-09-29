-- 023_break_minutes_net_hours.down.sql
-- 021'in bıraktığı brüt hâle döner.

DROP VIEW IF EXISTS v_fairness;
DROP VIEW IF EXISTS v_monthly_hours;
DROP VIEW IF EXISTS v_assignment_hours;
DROP VIEW IF EXISTS v_shift_types_net;

ALTER TABLE shift_types DROP CONSTRAINT IF EXISTS ck_shift_types_break;
ALTER TABLE shift_types DROP COLUMN IF EXISTS break_minutes;

CREATE VIEW v_assignment_hours AS
SELECT
    a.id AS assignment_id, a.draft_id, a.staff_id, a.work_date, a.source,
    st.code AS shift_code, st.crosses_midnight,
    (a.work_date + st.start_time) AT TIME ZONE 'Europe/Istanbul'                                        AS planned_start,
    (a.work_date + st.start_time + st.duration_hours * INTERVAL '1 hour') AT TIME ZONE 'Europe/Istanbul' AS planned_end,
    st.duration_hours                                                                                    AS planned_hours,
    COALESCE(act.actual_hours, st.duration_hours)                                                        AS worked_hours,
    COALESCE(GREATEST(0, ROUND((EXTRACT(EPOCH FROM (
        act.actual_end - (a.work_date + st.start_time + st.duration_hours * INTERVAL '1 hour') AT TIME ZONE 'Europe/Istanbul'
    )) / 3600)::numeric, 2)), 0)                                                                          AS late_exit_hours
FROM assignments a
JOIN shift_types st        ON st.id = a.shift_type_id
LEFT JOIN actual_times act ON act.assignment_id = a.id;

CREATE VIEW v_monthly_hours AS
WITH min_h AS (
    SELECT p.param_value AS min_hours
    FROM constraint_params p
    JOIN constraints c ON c.id = p.constraint_id
    WHERE c.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours'
)
SELECT
    d.id AS draft_id, lower(d.period) AS period_start, upper(d.period) AS period_end,
    s.id AS staff_id, s.full_name,
    COUNT(h.assignment_id)                    AS shift_count,
    COALESCE(SUM(h.planned_hours), 0)         AS planned_hours,
    COALESCE(SUM(h.worked_hours), 0)          AS worked_hours,
    m.min_hours,
    GREATEST(0, m.min_hours - COALESCE(SUM(h.worked_hours), 0))  AS missing_hours,
    GREATEST(0, COALESCE(SUM(h.worked_hours), 0) - m.min_hours)  AS overtime_monthly,
    COALESCE(SUM(h.late_exit_hours), 0)                          AS overtime_late_exit,
    GREATEST(GREATEST(0, COALESCE(SUM(h.worked_hours), 0) - m.min_hours),
             COALESCE(SUM(h.late_exit_hours), 0))                AS overtime_max
FROM schedule_drafts d
CROSS JOIN staff s
CROSS JOIN min_h m
LEFT JOIN v_assignment_hours h
       ON h.draft_id = d.id AND h.staff_id = s.id AND d.period @> h.work_date
WHERE s.is_active
   OR EXISTS (SELECT 1 FROM assignments a WHERE a.staff_id = s.id AND a.draft_id = d.id)
GROUP BY d.id, d.period, s.id, s.full_name, m.min_hours;

CREATE VIEW v_fairness AS
WITH per_staff AS (
    SELECT mh.draft_id, mh.staff_id, mh.full_name, mh.worked_hours,
        COUNT(h.assignment_id) FILTER (WHERE h.crosses_midnight) AS night_count,
        COUNT(h.assignment_id) FILTER (WHERE EXTRACT(ISODOW FROM h.work_date) IN (6, 7)) AS weekend_count
    FROM v_monthly_hours mh
    LEFT JOIN v_assignment_hours h
           ON h.draft_id = mh.draft_id AND h.staff_id = mh.staff_id
          AND h.work_date >= mh.period_start AND h.work_date < mh.period_end
    GROUP BY mh.draft_id, mh.staff_id, mh.full_name, mh.worked_hours
)
SELECT draft_id, staff_id, full_name, worked_hours, night_count, weekend_count,
    ROUND(worked_hours - AVG(worked_hours) OVER (PARTITION BY draft_id), 1) AS hours_vs_avg,
    ROUND(night_count - AVG(night_count) OVER (PARTITION BY draft_id), 1)   AS nights_vs_avg,
    RANK() OVER (PARTITION BY draft_id ORDER BY night_count DESC)           AS night_rank
FROM per_staff;
