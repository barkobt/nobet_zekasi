-- 024_weekly_patterns_and_coverage_role.up.sql
-- İzin desenleri (Bölüm 3) + kapsamaya kimin sayıldığının veriye taşınması.
--
-- İKİ HARDCODE KALDIRILIYOR
--   1) v_daily_coverage ve solver/model.py "ro.code <> 'sorumlu_hemsire'" diye
--      YAZIYORDU. Artık rolün kendi bayrağı var. Eğitim hemşiresi de ekip
--      sayısına girmiyor (Baran, 29.09): her hafta kesin gelir ama 5 kişilik
--      ekibin yerine geçmez.
--   2) Sorumlunun sabit programı (C-008) solver/model.py'de kod olarak duruyordu
--      (Pzt-Cum gündüz, Cmt kısa, Paz izin). Artık staff_weekly_patterns'ta veri.
--      Program değişirse kod değişmez.

-- ---------------------------------------------------------------------------
-- 1) Kapsamaya sayılan rol
-- ---------------------------------------------------------------------------
ALTER TABLE roles
    ADD COLUMN counts_toward_coverage BOOLEAN NOT NULL DEFAULT TRUE;

COMMENT ON COLUMN roles.counts_toward_coverage IS
    'Bu roldeki kişi ihtiyaç şablonundaki GENEL mevcuda sayılır mı. '
    'Sorumlu hemşire ve eğitim hemşiresi sayılmaz: çalışırlar ama ekip kadrosunun yerine geçmezler.';

-- ---------------------------------------------------------------------------
-- 2) Kişi bazlı haftalık desen
-- ---------------------------------------------------------------------------
-- Üç tür, üçü de KATI:
--   SABIT_VARDIYA  o hafta günü kişi MUTLAKA bu vardiyada (seçim değil, girdi)
--   SABIT_OFF      o hafta günü kişi MUTLAKA boş
--   OFF_OLABILIR   kişinin haftalık izin günü bu günlerden BİRİ olmak zorunda
--
-- isodow: ISO hafta günü, 1 = Pazartesi … 7 = Pazar. Takvim haftası Pzt–Paz
-- (Edem teyidi, 29.09) — kayan 7 gün değil.
--
-- Kişi başına gün başına tek satır: aynı güne hem SABIT_OFF hem SABIT_VARDIYA
-- yazılamasın.
CREATE TABLE staff_weekly_patterns (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_id      BIGINT   NOT NULL,
    isodow        SMALLINT NOT NULL,
    kind          TEXT     NOT NULL,
    shift_type_id BIGINT,
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_swp_staff FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT fk_swp_shift FOREIGN KEY (shift_type_id) REFERENCES shift_types(id) ON DELETE RESTRICT,
    CONSTRAINT uq_swp_staff_day UNIQUE (staff_id, isodow),
    CONSTRAINT ck_swp_isodow CHECK (isodow BETWEEN 1 AND 7),
    CONSTRAINT ck_swp_kind CHECK (kind IN ('SABIT_VARDIYA', 'SABIT_OFF', 'OFF_OLABILIR')),
    -- Vardiya YALNIZ SABIT_VARDIYA'da anlamlı; diğerlerinde dolu olması
    -- "boş günde şu vardiyada çalışsın" gibi çelişkili bir kayıt olurdu.
    CONSTRAINT ck_swp_shift_only_for_fixed CHECK (
        (kind = 'SABIT_VARDIYA' AND shift_type_id IS NOT NULL)
        OR (kind <> 'SABIT_VARDIYA' AND shift_type_id IS NULL)
    )
);

COMMENT ON TABLE staff_weekly_patterns IS
    'Kişiye özel haftalık çalışma deseni. Sorumlunun sabit programı ve eğitim '
    'hemşiresinin hafta sonu izni burada durur; koda gömülü değildir.';

CREATE INDEX ix_swp_staff ON staff_weekly_patterns (staff_id);

-- ---------------------------------------------------------------------------
-- 3) Kapsama view'ı: rol adı yerine bayrak
-- ---------------------------------------------------------------------------
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
                THEN (NOT s.is_orientation AND ro.counts_toward_coverage)
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
