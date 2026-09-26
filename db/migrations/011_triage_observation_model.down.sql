-- 011_triage_observation_model.down.sql
-- Ters sıra: trigger ve fonksiyon düşer, iki view 010'daki tanımına döner.
-- View'lardan kolon DÜŞÜRMEK CREATE OR REPLACE ile mümkün değil → DROP + CREATE.

DROP TRIGGER IF EXISTS assignment_tasks_check_exclusivity ON assignment_tasks;
DROP FUNCTION IF EXISTS trg_assignment_tasks_check_exclusivity();

DROP VIEW IF EXISTS v_task_eligibility_violations;
CREATE VIEW v_task_eligibility_violations AS
SELECT
    a.draft_id, a.id AS assignment_id, a.staff_id, s.full_name, a.work_date,
    st.code AS shift_code, c.code AS task_code, c.name AS task_name, a.source
FROM assignment_tasks t
JOIN assignments a   ON a.id  = t.assignment_id
JOIN staff s         ON s.id  = a.staff_id
JOIN shift_types st  ON st.id = a.shift_type_id
JOIN competencies c  ON c.id  = t.competency_id
WHERE NOT EXISTS (
    SELECT 1 FROM staff_competencies sc
    WHERE sc.staff_id = a.staff_id AND sc.competency_id = t.competency_id
);

DROP VIEW IF EXISTS v_daily_coverage;
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
    )              AS assigned
FROM days
JOIN need_periods np        ON np.unit_id = days.unit_id AND np.valid_period @> days.day
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
JOIN shift_types nst        ON nst.id = ntr.shift_type_id;
