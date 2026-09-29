-- 024_weekly_patterns_and_coverage_role.down.sql
-- 012'nin bıraktığı hâle döner: kapsama dışı rol yeniden koda (view'a) gömülü.

DROP TABLE IF EXISTS staff_weekly_patterns;
DROP VIEW IF EXISTS v_daily_coverage;

CREATE VIEW v_daily_coverage AS
WITH days AS (
    SELECT d.id AS draft_id, d.unit_id, gs::date AS day
    FROM schedule_drafts d,
         generate_series(lower(d.period), (upper(d.period) - 1), INTERVAL '1 day') AS gs
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

-- View, sütuna bağımlı olduğu için sütun EN SONDA düşürülür.
ALTER TABLE roles DROP COLUMN IF EXISTS counts_toward_coverage;
