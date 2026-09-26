-- 011_triage_observation_model.up.sql
-- 26.09.2026 saha düzeltmesi: vardiyadaki her çalışan (sorumlu ve oryantasyon hariç)
-- ya triyajda ya gözlemdedir; ikisi birden olamaz. Ambulans dönüşlü bir görevdir,
-- gidenler kendi alanlarının sayısından düşmez ama ambulans çıkınca her iki alanda
-- en az 1 kişi kalmalıdır.
--
-- Bu dosya YAPIyı kurar: ayrıklık trigger'ı + iki yeni ölçü kolonu.
-- Kural satırları ve referans haftanın türetilmiş rozetleri seeds/011'de.

---------------------------------------------------------------------------
-- A) TRIYAJ ile GÖZLEM aynı atamada olamaz  (C-010'un ayrıklık yarısı)
---------------------------------------------------------------------------
-- Kalıp, uygunluk trigger'ıyla aynı: trigger PLANI korur, GEÇMİŞİ yeniden yazmaz.
--   source='solver'                → hata
--   source='manuel' / 'onceki_ay'  → uyarı, kayıt alınır
-- İhlaller v_task_eligibility_violations'ta görünür.
CREATE FUNCTION trg_assignment_tasks_check_exclusivity() RETURNS trigger AS $$
DECLARE
    v_yeni     TEXT;
    v_cakisan  TEXT;
    v_source   TEXT;
    v_name     TEXT;
BEGIN
    SELECT code INTO v_yeni FROM competencies WHERE id = NEW.competency_id;
    IF v_yeni NOT IN ('TRIYAJ', 'GOZLEM') THEN
        RETURN NEW;
    END IF;
    v_cakisan := CASE v_yeni WHEN 'TRIYAJ' THEN 'GOZLEM' ELSE 'TRIYAJ' END;

    IF NOT EXISTS (
        SELECT 1 FROM assignment_tasks t
        JOIN competencies c ON c.id = t.competency_id
        WHERE t.assignment_id = NEW.assignment_id AND c.code = v_cakisan
    ) THEN
        RETURN NEW;
    END IF;

    SELECT a.source, s.full_name INTO v_source, v_name
    FROM assignments a JOIN staff s ON s.id = a.staff_id
    WHERE a.id = NEW.assignment_id;

    IF v_source = 'solver' THEN
        RAISE EXCEPTION
            '% ayni vardiyada hem TRIYAJ hem GOZLEM alamaz.', v_name
            USING ERRCODE = 'check_violation';
    END IF;
    RAISE WARNING
        '% ayni vardiyada hem TRIYAJ hem GOZLEM (kaynak: %). Kayit alindi.', v_name, v_source;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER assignment_tasks_check_exclusivity
    BEFORE INSERT OR UPDATE ON assignment_tasks
    FOR EACH ROW EXECUTE FUNCTION trg_assignment_tasks_check_exclusivity();

---------------------------------------------------------------------------
-- B) Denetim view'ı ayrıklık ihlallerini de görsün
---------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_task_eligibility_violations AS
-- 1) Yetkinliği olmayana verilen görev (010'dan)
SELECT a.draft_id, a.id AS assignment_id, a.staff_id, s.full_name, a.work_date,
       st.code AS shift_code, c.code AS task_code, c.name AS task_name, a.source,
       'yetkinlik_yok'::text AS violation_type
FROM assignment_tasks t
JOIN assignments a  ON a.id  = t.assignment_id
JOIN staff s        ON s.id  = a.staff_id
JOIN shift_types st ON st.id = a.shift_type_id
JOIN competencies c ON c.id  = t.competency_id
WHERE NOT EXISTS (SELECT 1 FROM staff_competencies sc
                  WHERE sc.staff_id = a.staff_id AND sc.competency_id = t.competency_id)
UNION ALL
-- 2) Aynı atamada hem TRIYAJ hem GOZLEM
SELECT a.draft_id, a.id, a.staff_id, s.full_name, a.work_date,
       -- UNION'da tipler birebir eşleşmeli: mevcut view'ın kolonları
       -- competencies.code/name'den geliyor, literal'leri aynı tipe çeviriyoruz.
       st.code, 'TRIYAJ+GOZLEM'::varchar(50),
       'Triyaj ve gözlem aynı vardiyada'::varchar(100), a.source,
       'triyaj_gozlem_cakismasi'::text
FROM assignments a
JOIN staff s        ON s.id  = a.staff_id
JOIN shift_types st ON st.id = a.shift_type_id
WHERE EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id=t.competency_id
              WHERE t.assignment_id=a.id AND c.code='TRIYAJ')
  AND EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies c ON c.id=t.competency_id
              WHERE t.assignment_id=a.id AND c.code='GOZLEM');

---------------------------------------------------------------------------
-- C) v_daily_coverage: yetkin sayısı + ambulans sonrası kalan
---------------------------------------------------------------------------
-- CREATE OR REPLACE yalnızca SONA kolon eklemeye izin verir; mevcut altı kolon
-- aynı sırada ve aynı tipte kalıyor, iki yeni kolon sonda.
--   qualified                  = o vardiyada slotun istediği yetkinliğe SAHİP kişi sayısı
--                                (rozet değil yetkinlik; GENEL slotunda anlamsız → NULL)
--   remaining_after_ambulance  = TRIYAJ/GOZLEM için: bu görevi taşıyıp ambulansa
--                                ÇIKMAYAN kişi sayısı. Diğer slotlarda NULL.
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
