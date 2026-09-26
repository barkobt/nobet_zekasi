-- 012_draft_period.down.sql
-- period → month_start. Ay başına denk gelmeyen aralıklar KAYBOLUR: geri dönüşte
-- aralığın başladığı ayın 1'i alınır. Bu kayıplı bir dönüştürmedir, bilerek.

DROP VIEW IF EXISTS v_fairness;
DROP VIEW IF EXISTS v_monthly_hours;
DROP VIEW IF EXISTS v_daily_coverage;

ALTER TABLE schedule_drafts ADD COLUMN month_start DATE;
UPDATE schedule_drafts SET month_start = date_trunc('month', lower(period))::date;
ALTER TABLE schedule_drafts ALTER COLUMN month_start SET NOT NULL;
ALTER TABLE schedule_drafts
    ADD CONSTRAINT ck_drafts_month_start CHECK (EXTRACT(DAY FROM month_start) = 1);

ALTER TABLE schedule_drafts
    DROP CONSTRAINT IF EXISTS ex_drafts_one_published,
    DROP CONSTRAINT IF EXISTS ck_drafts_period_bounded,
    DROP COLUMN IF EXISTS period;

CREATE UNIQUE INDEX uq_drafts_one_published
    ON schedule_drafts (unit_id, month_start)
    WHERE status = 'yayinlandi';

CREATE VIEW v_monthly_hours AS
WITH min_h AS (
    SELECT p.param_value AS min_hours
    FROM constraint_params p
    JOIN constraints c ON c.id = p.constraint_id
    WHERE c.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours'
)
SELECT
    d.id                                      AS draft_id,
    d.month_start,
    s.id                                      AS staff_id,
    s.full_name,
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
       ON h.draft_id = d.id
      AND h.staff_id = s.id
      AND h.work_date >= d.month_start
      AND h.work_date <  (d.month_start + INTERVAL '1 month')
WHERE s.is_active
GROUP BY d.id, d.month_start, s.id, s.full_name, m.min_hours;

CREATE VIEW v_fairness AS
WITH per_staff AS (
    SELECT
        mh.draft_id,
        mh.staff_id,
        mh.full_name,
        mh.worked_hours,
        COUNT(h.assignment_id) FILTER (WHERE h.crosses_midnight)                      AS night_count,
        COUNT(h.assignment_id) FILTER (WHERE EXTRACT(ISODOW FROM h.work_date) IN (6, 7)) AS weekend_count
    FROM v_monthly_hours mh
    LEFT JOIN v_assignment_hours h
           ON h.draft_id = mh.draft_id
          AND h.staff_id = mh.staff_id
          AND h.work_date >= mh.month_start
          AND h.work_date <  (mh.month_start + INTERVAL '1 month')
    GROUP BY mh.draft_id, mh.staff_id, mh.full_name, mh.worked_hours
)
SELECT
    draft_id,
    staff_id,
    full_name,
    worked_hours,
    night_count,
    weekend_count,
    ROUND(worked_hours - AVG(worked_hours) OVER (PARTITION BY draft_id), 1) AS hours_vs_avg,
    ROUND(night_count  - AVG(night_count)  OVER (PARTITION BY draft_id), 1) AS nights_vs_avg,
    RANK() OVER (PARTITION BY draft_id ORDER BY night_count DESC)           AS night_rank
FROM per_staff;

CREATE VIEW v_daily_coverage AS
WITH days AS (
    SELECT d.id AS draft_id, d.unit_id, gs::date AS day
    FROM schedule_drafts d,
         generate_series(d.month_start,
                         (d.month_start + INTERVAL '1 month' - INTERVAL '1 day')::date,
                         INTERVAL '1 day') AS gs
)
SELECT
    days.draft_id,
    days.day,
    nst.code       AS shift_code,
    ntr.slot_code,
    ntr.min_count  AS required,
    (
        SELECT COUNT(*)
        FROM assignments a
        JOIN shift_types ast ON ast.id = a.shift_type_id
        JOIN staff s         ON s.id  = a.staff_id
        JOIN roles ro        ON ro.id = s.role_id
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.unit_id = nst.unit_id
          AND ast.start_time = nst.start_time
          AND CASE
                WHEN NOT EXISTS (SELECT 1 FROM need_template_row_competencies x
                                 WHERE x.need_template_row_id = ntr.id)
                THEN (NOT s.is_orientation AND ro.code <> 'sorumlu_hemsire')
                ELSE NOT EXISTS (
                    SELECT 1
                    FROM need_template_row_competencies x
                    JOIN competencies c ON c.id = x.competency_id
                    WHERE x.need_template_row_id = ntr.id
                      AND NOT (
                          (c.kind = 'TASK' AND EXISTS (
                              SELECT 1 FROM assignment_tasks t
                              WHERE t.assignment_id = a.id AND t.competency_id = c.id))
                          OR
                          (c.kind = 'QUALIFICATION' AND EXISTS (
                              SELECT 1 FROM staff_competencies sc
                              WHERE sc.staff_id = a.staff_id AND sc.competency_id = c.id))
                      )
                )
              END
    )              AS assigned,
    -- YENİ: yetkin kişi sayısı (rozetten bağımsız)
    CASE WHEN EXISTS (SELECT 1 FROM need_template_row_competencies x
                      WHERE x.need_template_row_id = ntr.id)
    THEN (
        SELECT COUNT(*)
        FROM assignments a
        JOIN shift_types ast ON ast.id = a.shift_type_id
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.unit_id = nst.unit_id
          AND ast.start_time = nst.start_time
          AND NOT EXISTS (
              SELECT 1 FROM need_template_row_competencies x
              WHERE x.need_template_row_id = ntr.id
                AND NOT EXISTS (SELECT 1 FROM staff_competencies sc
                                WHERE sc.staff_id = a.staff_id AND sc.competency_id = x.competency_id)
          )
    ) END          AS qualified,
    -- YENİ: ambulansa çıkanlar düşüldükten sonra alanda kalan
    CASE WHEN ntr.slot_code IN ('TRIYAJ', 'GOZLEM')
    THEN (
        SELECT COUNT(*)
        FROM assignments a
        JOIN shift_types ast ON ast.id = a.shift_type_id
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.unit_id = nst.unit_id
          AND ast.start_time = nst.start_time
          AND EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id=t.competency_id
                      WHERE t.assignment_id=a.id AND c.code = ntr.slot_code)
          AND NOT EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id=t.competency_id
                          WHERE t.assignment_id=a.id AND c.code = 'AMBULANS')
    ) END          AS remaining_after_ambulance
FROM days
JOIN need_periods np        ON np.unit_id = days.unit_id AND np.valid_period @> days.day
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
JOIN shift_types nst        ON nst.id = ntr.shift_type_id;
