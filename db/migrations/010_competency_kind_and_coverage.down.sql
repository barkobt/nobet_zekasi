-- 010_competency_kind_and_coverage.down.sql
-- Ters sıra: önce 010'un eklediği nesneler, sonra view 009'daki haline döner, en son kolonlar.

DROP VIEW IF EXISTS v_task_eligibility_violations;

DROP TRIGGER IF EXISTS assignment_tasks_check_eligibility ON assignment_tasks;
DROP FUNCTION IF EXISTS trg_assignment_tasks_check_eligibility();

-- v_daily_coverage: 009'daki tanıma geri dön (kind yok, birim filtresi yok).
CREATE OR REPLACE VIEW v_daily_coverage AS
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
        JOIN staff s  ON s.id = a.staff_id
        JOIN roles ro ON ro.id = s.role_id
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.start_time = nst.start_time
          AND (
                (ntr.slot_code = 'GENEL' AND NOT s.is_orientation AND ro.code <> 'sorumlu_hemsire')
                OR EXISTS (
                    SELECT 1
                    FROM assignment_tasks t
                    JOIN competencies c ON c.id = t.competency_id
                    WHERE t.assignment_id = a.id AND c.code = ntr.slot_code
                )
              )
    )              AS assigned
FROM days
JOIN need_periods np        ON np.unit_id = days.unit_id AND np.valid_period @> days.day
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
JOIN shift_types nst        ON nst.id = ntr.shift_type_id;

ALTER TABLE need_template_rows
    DROP CONSTRAINT IF EXISTS fk_ntr_constraint,
    DROP COLUMN IF EXISTS constraint_id;

ALTER TABLE constraints
    DROP CONSTRAINT IF EXISTS uq_constraints_catalog_code,
    DROP COLUMN IF EXISTS catalog_code;

ALTER TABLE competencies
    DROP CONSTRAINT IF EXISTS ck_competencies_kind,
    DROP COLUMN IF EXISTS kind;
