-- 008_integrity_and_views.up.sql
-- Adım 7 (bütünlük) + Adım 9 (türetilmiş görünümler)
-- Adım 8 (indeks) için ek bir şey YOK, sebebi en altta.

---------------------------------------------------------------------------
-- A) BÜTÜNLÜK KURALLARI
---------------------------------------------------------------------------

-- Ayrılan personel SİLİNMEZ, pasife alınır. (assignments.staff_id RESTRICT olduğu için
-- geçmiş ataması olan kişi zaten silinemez; bu kolon "artık planlama dışı" demenin yolu.)
ALTER TABLE staff
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;

-- Vardiya süresi 0'dan büyük, en fazla 24 saat.
ALTER TABLE shift_types
    ADD CONSTRAINT ck_shift_types_duration CHECK (duration_hours > 0 AND duration_hours <= 24);

-- Sözleşme: hedef saat boşsa "kural varsayılanı (200) geçerli" demektir; doluysa pozitif olmalı.
-- Başlangıç tarihi zorunlu (lower_inf = başlangıcı sonsuz/boş aralık), bitiş açık kalabilir.
ALTER TABLE contracts
    ADD CONSTRAINT ck_contracts_target_positive CHECK (monthly_target_hours IS NULL OR monthly_target_hours > 0),
    ADD CONSTRAINT ck_contracts_period_has_start CHECK (NOT isempty(valid_period) AND NOT lower_inf(valid_period));

-- İzin: hem başlangıcı hem bitişi belli olmalı. "Süresiz izin" bir izin değil, ayrılıştır.
ALTER TABLE absences
    ADD CONSTRAINT ck_absences_period_bounded
    CHECK (NOT isempty(period) AND NOT lower_inf(period) AND NOT upper_inf(period));

-- İhtiyaç dönemi: başlangıç zorunlu, bitiş açık kalabilir ("1 Eylül'den itibaren").
ALTER TABLE need_periods
    ADD CONSTRAINT ck_need_periods_has_start CHECK (NOT isempty(valid_period) AND NOT lower_inf(valid_period));

---------------------------------------------------------------------------
-- B) GÖRÜNÜMLER (VIEW) — veri tutmaz, her okunuşta tablolardan hesaplanır
---------------------------------------------------------------------------

-- B1) Uyumsuz çiftler, iki yönlü.
-- staff_conflicts çifti tek satırda (küçük id, büyük id) tutuyor. "Deniz kimlerle uyumsuz?"
-- sorusu için iki yöne de bakmak gerekir; bu view o işi bir kez yapar.
CREATE VIEW v_staff_conflict_pairs AS
SELECT staff_id_low  AS staff_id, staff_id_high AS other_staff_id, note FROM staff_conflicts
UNION ALL
SELECT staff_id_high AS staff_id, staff_id_low  AS other_staff_id, note FROM staff_conflicts;

-- B2) Atama başına planlanan ve gerçekleşen saat.
-- Planlanan başlangıç = work_date + start_time (DATE + TIME = TIMESTAMP).
-- AT TIME ZONE 'Europe/Istanbul': yerel saati, actual_times'taki TIMESTAMPTZ ile karşılaştırılabilir hale getirir.
-- worked_hours: gerçekleşen kayıt varsa onu, yoksa planı kullan (COALESCE = "ilk boş olmayanı al").
-- late_exit_hours: planlanan çıkıştan sonra kalınan süre (geç çıkış mesaisi).
CREATE VIEW v_assignment_hours AS
SELECT
    a.id            AS assignment_id,
    a.draft_id,
    a.staff_id,
    a.work_date,
    a.source,
    st.code         AS shift_code,
    st.crosses_midnight,
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

-- B3) Aylık puantaj (E-11): taslak × aktif personel.
-- CROSS JOIN staff + LEFT JOIN: hiç ataması olmayan kişi de 0 saatle görünür (yoksa listeden kaybolurdu).
-- Ay filtresi LEFT JOIN'in ON koşulunda: önceki aydan bağlam olarak gelen satırlar sayılmaz.
-- min_hours kodda yazılı değil, constraint_params'tan okunuyor → kural değişince rapor da değişir.
-- İki fazla mesai tanımı yan yana (karar hastanede):
--   overtime_monthly  = aylık toplamın 200'ü aşan kısmı
--   overtime_late_exit = geç çıkışların toplamı
--   overtime_max      = ikisinden büyüğü (çifte saymayan birleşik tanım)
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

-- B4) Adalet panosu (E-12): gece sayısı, hafta sonu sayısı, ortalamadan sapma.
-- WINDOW FUNCTION: AVG(...) OVER (PARTITION BY draft_id) → her satırın yanına, satırları
-- gruplamadan (GROUP BY'daki gibi tek satıra indirmeden) "bu taslağın ortalaması"nı yazar.
-- Gece = crosses_midnight (aktif vardiyalar içinde ertesi güne taşan tek vardiya GECE).
-- ISODOW: Pazartesi=1 ... Pazar=7 → 6 ve 7 hafta sonu.
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

-- B5) Günlük kapsama (E-09 sütun başlığındaki "atanan / gereken").
-- 1. Taslağın ayındaki her günü üret (generate_series).
-- 2. O gün hangi şablon geçerliyse (need_periods @> gün) onun satırlarını getir.
--    @> = "aralık bu tarihi içeriyor mu?"
-- 3. Her satır için atanan sayısını say:
--    GENEL slotu → o vardiyadaki tüm atamalar
--    Diğer slotlar → o vardiyada, görevi slot koduyla aynı olan atamalar (TRIYAJ slotu → TRIYAJ görevi)
-- Vardiya eşleşmesi başlangıç saatiyle: 08:30'da başlayan herkes gündüz ekibindendir
-- (Sorumlu'nun kısa Cumartesi vardiyası GUNDUZ_CMT de gündüz mevcuduna sayılır).
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
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.start_time = nst.start_time
          AND (
                ntr.slot_code = 'GENEL'
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

---------------------------------------------------------------------------
-- C) İNDEKSLER — neden yeni indeks eklemedik?
---------------------------------------------------------------------------
-- En sık sorgular:
--   "Bu taslakta 14 Ekim'de kimler var?"      → WHERE draft_id = ? AND work_date = ?
--   "Bu taslakta Ayşe'nin ay toplamı?"         → WHERE draft_id = ? AND staff_id = ?
-- uq_assignments_draft_staff_date UNIQUE kısıtı PostgreSQL'e zaten (draft_id, staff_id, work_date)
-- sırasıyla bir indeks kurdurdu. İlk kolonu draft_id olduğu için iki sorgu da bu indeksi kullanır.
-- 18 kişi × 31 gün × birkaç taslak = birkaç bin satır: ek indeks ölçülebilir fark yaratmaz.
-- Kural: önce sorguyu yaz, EXPLAIN ANALYZE ile ölç, yavaşsa indeksle (queries/checks.sql'de örnek var).
