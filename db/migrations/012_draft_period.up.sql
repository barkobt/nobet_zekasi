-- 012_draft_period.up.sql
-- Taslak artık bir AYA değil, bir TARİH ARALIĞINA bağlı: 1 gün, 1 hafta, 1 ay ya da
-- herhangi bir aralık. month_start kolonu period DATERANGE ile değiştiriliyor.
-- herhangi bir aralık. month_start kolonu period DATERANGE ile değiştiriliyor.
--
-- DATERANGE seçimi: contracts, absences ve need_periods zaten böyle. Çakışma kontrolü
-- (&&) ve "şu günü içeriyor mu" (@>) doğrudan gelir; iki ayrı DATE kolonuyla bunları
-- elle yazmak gerekirdi.

---------------------------------------------------------------------------
-- A) Kolon
---------------------------------------------------------------------------
ALTER TABLE schedule_drafts ADD COLUMN period DATERANGE;

-- Mevcut ay taslaklarını kayıpsız taşı: [ayın 1'i, ertesi ayın 1'i)
-- Migration'lar seed'lerden önce koştuğu için TAZE kurulumda bu UPDATE 0 satır etkiler;
-- orada veriyi seeds/009 doğrudan period ile yazar. Bu satır YALNIZCA mevcut
-- veritabanlarını (yerel, Neon) taşımak için var.
UPDATE schedule_drafts
SET period = daterange(month_start, (month_start + INTERVAL '1 month')::date, '[)')
WHERE period IS NULL;

ALTER TABLE schedule_drafts ALTER COLUMN period SET NOT NULL;

-- Boş aralık anlamsız; başlangıç ve bitiş belli olmalı (absences'taki kalıp).
ALTER TABLE schedule_drafts
    ADD CONSTRAINT ck_drafts_period_bounded
    CHECK (NOT isempty(period) AND NOT lower_inf(period) AND NOT upper_inf(period));

---------------------------------------------------------------------------
-- B) "Aynı dönemde tek yayınlanmış taslak" — artık aralık çakışmasına göre
---------------------------------------------------------------------------
-- Eskisi (unit_id, month_start) üzerinde kısmi UNIQUE indeksti; serbest aralıklarda
-- bu yetmez: 1–7 Ekim ile 5–12 Ekim farklı month_start'a sahip ama çakışıyorlar.
DROP INDEX IF EXISTS uq_drafts_one_published;

ALTER TABLE schedule_drafts
    ADD CONSTRAINT ex_drafts_one_published
    EXCLUDE USING gist (unit_id WITH =, period WITH &&)
    WHERE (status = 'yayinlandi');

---------------------------------------------------------------------------
-- C) month_start'ı düşür ve ona bağlı view'ları yeniden tanımla
---------------------------------------------------------------------------
-- v_fairness → v_monthly_hours → schedule_drafts zinciri olduğu için ters sırayla
-- düşürülüp yeniden kuruluyor. v_daily_coverage bağımsız, CREATE OR REPLACE yeter
-- (kolonları aynı kalıyor).
-- v_daily_coverage de month_start'a bakıyor (days CTE), o da düşmeli.
DROP VIEW IF EXISTS v_fairness;
DROP VIEW IF EXISTS v_monthly_hours;
DROP VIEW IF EXISTS v_daily_coverage;

ALTER TABLE schedule_drafts DROP COLUMN month_start;   -- ck_drafts_month_start ile birlikte düşer

-- C1) Puantaj: artık "ay" değil "taslağın dönemi".
--     Kolon adları period_start / period_end oldu; min_hours aylık 200 saat hedefi
--     olarak kalıyor ama karşılaştırma ancak dönem bir ayı kapsıyorsa anlamlı
--     (API covers_full_month ile bunu zaten ayırt ediyor).
CREATE VIEW v_monthly_hours AS
WITH min_h AS (
    SELECT p.param_value AS min_hours
    FROM constraint_params p
    JOIN constraints c ON c.id = p.constraint_id
    WHERE c.code = 'monthly_min_hours' AND p.param_key = 'monthly_min_hours'
)
SELECT
    d.id                                      AS draft_id,
    lower(d.period)                           AS period_start,
    upper(d.period)                           AS period_end,
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
      AND d.period @> h.work_date      -- aralık içindekiler; önceki ay bağlamı sayılmaz
WHERE s.is_active
GROUP BY d.id, d.period, s.id, s.full_name, m.min_hours;

-- C2) Adalet panosu: yalnızca month_start referansları period'a çevrildi.
CREATE VIEW v_fairness AS
WITH per_staff AS (
    SELECT
        mh.draft_id, mh.staff_id, mh.full_name, mh.worked_hours,
        COUNT(h.assignment_id) FILTER (WHERE h.crosses_midnight)                         AS night_count,
        COUNT(h.assignment_id) FILTER (WHERE EXTRACT(ISODOW FROM h.work_date) IN (6, 7)) AS weekend_count
    FROM v_monthly_hours mh
    LEFT JOIN v_assignment_hours h
           ON h.draft_id = mh.draft_id
          AND h.staff_id = mh.staff_id
          AND h.work_date >= mh.period_start
          AND h.work_date <  mh.period_end
    GROUP BY mh.draft_id, mh.staff_id, mh.full_name, mh.worked_hours
)
SELECT
    draft_id, staff_id, full_name, worked_hours, night_count, weekend_count,
    ROUND(worked_hours - AVG(worked_hours) OVER (PARTITION BY draft_id), 1) AS hours_vs_avg,
    ROUND(night_count  - AVG(night_count)  OVER (PARTITION BY draft_id), 1) AS nights_vs_avg,
    RANK() OVER (PARTITION BY draft_id ORDER BY night_count DESC)           AS night_rank
FROM per_staff;

-- C3) Kapsama: 011'deki tanımın aynısı; tek fark gün üretiminin aralıktan gelmesi.
CREATE VIEW v_daily_coverage AS
WITH days AS (
    SELECT d.id AS draft_id, d.unit_id, gs::date AS day
    FROM schedule_drafts d,
         generate_series(lower(d.period),
                         (upper(d.period) - 1),   -- '[)' üst sınır dışlayıcı
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
