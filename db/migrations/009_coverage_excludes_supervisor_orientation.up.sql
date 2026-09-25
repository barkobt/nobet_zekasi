-- 009_coverage_excludes_supervisor_orientation.up.sql
-- 24.09 kararı: Oryantasyondakiler ve sorumlu hemşire vardiya mevcuduna (GENEL) sayılmaz.
-- View = şemanın parçası → değişikliği yeni migration.
-- CREATE OR REPLACE VIEW: kolonlar aynı kaldığı sürece view'ı silmeden yeniden tanımlar.
-- Değişen tek yer: GENEL slotu sayılırken staff ve roles'a bakan iki JOIN ve koşul.

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
                -- GENEL: sorumlu ve oryantasyondakiler mevcuda SAYILMAZ (24.09 kararı)
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
