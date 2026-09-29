-- 023_break_minutes_net_hours.up.sql
-- Molalar mesaiye DAHİL DEĞİL. Net saat hesabı.
--
-- BULGU (29.09.2026): molayı mesaiden saydığımız için brüt saatle 200 saatlik
-- aylık hedef 3-4 günde doluyordu; solver kalan günleri boş bırakıyordu.
-- "3 gün üst üste boşluk" şikâyeti bunun doğrudan sonucuydu.
--
-- KURAL (Edem): gündüz molası 1 sa 20 dk (80 dk), gece molası 3 sa 30 dk (210 dk).
-- Molanın ne zaman kullanıldığı bilinmiyor ve önemsiz — yalnız süreden düşülür.
--
-- NE BRÜT KALIR, NE NET OLUR
--   BRÜT  planned_start / planned_end (gerçek saat aralığı), late_exit_hours,
--         actual_times'taki HAM veri, vardiya arası dinlenme / gece→gündüz
--         kontrolü. Mola dinlenme sayılmaz; saat aralığı gerçek zamandır.
--   NET   aylık 200 sa hedefi, haftalık 50 sa referansı, adalet farkı,
--         personel özeti, raporlar, Excel, solver amaç fonksiyonu.
--
-- actual_times DEĞİŞMİYOR: saklanan ham veri brüt kalır, net hesap anında
-- türetilir (Baran, 29.09). Böylece mola süresi ileride değişirse geçmiş
-- kayıtlar yeniden yazılmaz, yalnız view başka bir sonuç üretir.

ALTER TABLE shift_types
    ADD COLUMN break_minutes INT NOT NULL DEFAULT 0;

-- Mola vardiyadan uzun olamaz; eşit de olamaz (net 0 saatlik vardiya anlamsız).
-- Arayüzden düzenlenebilir bir alan olduğu için sınır veritabanında duruyor:
-- 600 dakika yazan birine hata API'de değil, şemada çıkar.
ALTER TABLE shift_types
    ADD CONSTRAINT ck_shift_types_break
    CHECK (break_minutes >= 0 AND break_minutes < duration_hours * 60);

COMMENT ON COLUMN shift_types.break_minutes IS
    'Vardiya içindeki toplam mola (dakika). Mesaiye dahil DEĞİL, net süreden düşülür.';

-- ---------------------------------------------------------------------------
-- Net sürenin TEK tanımı. Başka hiçbir yerde "süre eksi mola" aritmetiği
-- yazılmaz; her tüketici buradan okur. Mola kuralı değişirse tek yer değişir.
-- ---------------------------------------------------------------------------
CREATE VIEW v_shift_types_net AS
SELECT
    st.id, st.unit_id, st.code, st.name, st.start_time,
    st.duration_hours, st.crosses_midnight, st.is_active, st.break_minutes,
    (st.duration_hours * 60)::int                                   AS gross_minutes,
    (st.duration_hours * 60)::int - st.break_minutes                AS net_minutes,
    -- Dakikadan saate çevirim yalnız GÖSTERİM içindir. Hesap her zaman
    -- dakikayla yapılır: gündüz neti 8 sa 10 dk, saat cinsinden devirli
    -- bir ondalık (8,1666…) ve yuvarlanırsa aylık toplam kayar.
    ROUND(((st.duration_hours * 60)::int - st.break_minutes) / 60.0, 4) AS net_hours
FROM shift_types st;

COMMENT ON VIEW v_shift_types_net IS
    'Vardiya süresinin tek doğruluk kaynağı: brüt, mola ve net dakika.';

-- ---------------------------------------------------------------------------
-- Bağımlı view'lar. Zincir: v_fairness → v_monthly_hours → v_assignment_hours
-- olduğu için ters sırayla düşürülüp düz sırayla kuruluyor.
-- ---------------------------------------------------------------------------
DROP VIEW IF EXISTS v_fairness;
DROP VIEW IF EXISTS v_monthly_hours;
DROP VIEW IF EXISTS v_assignment_hours;

CREATE VIEW v_assignment_hours AS
SELECT
    a.id            AS assignment_id,
    a.draft_id,
    a.staff_id,
    a.work_date,
    a.source,
    st.code         AS shift_code,
    st.crosses_midnight,
    -- BRÜT: gerçek saat aralığı. Mola bu aralığın İÇİNDE geçer, aralığı kısaltmaz.
    (a.work_date + st.start_time) AT TIME ZONE 'Europe/Istanbul'                                        AS planned_start,
    (a.work_date + st.start_time + st.duration_hours * INTERVAL '1 hour') AT TIME ZONE 'Europe/Istanbul' AS planned_end,
    st.duration_hours                                                                                    AS planned_hours,
    COALESCE(act.actual_hours, st.duration_hours)                                                        AS worked_hours,
    -- NET: mesaiden sayılan süre. Dakika birincil, saat gösterim içindir.
    st.break_minutes                                                                                     AS break_minutes,
    st.net_minutes                                                                                       AS planned_net_minutes,
    (COALESCE(act.actual_hours, st.duration_hours) * 60)::int - st.break_minutes                         AS worked_net_minutes,
    COALESCE(GREATEST(0, ROUND((EXTRACT(EPOCH FROM (
        act.actual_end - (a.work_date + st.start_time + st.duration_hours * INTERVAL '1 hour') AT TIME ZONE 'Europe/Istanbul'
    )) / 3600)::numeric, 2)), 0)                                                                          AS late_exit_hours
FROM assignments a
JOIN v_shift_types_net st  ON st.id = a.shift_type_id
LEFT JOIN actual_times act ON act.assignment_id = a.id;

-- Aylık puantaj. planned_hours / worked_hours adları BİLEREK KALDIRILDI:
-- anlamları brütten nete dönseydi, güncellemeyi kaçıran her tüketici sessizce
-- yanlış sayı gösterirdi. Yeni adlar (net_hours / gross_hours) kaçırılan yeri
-- "column does not exist" ile YÜKSEK SESLE düşürür.
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
    -- Toplama DAKİKA ile yapılır, saate en sonda çevrilir: her vardiyayı ayrı
    -- yuvarlayıp toplasaydık 20 vardiyada saatlerce kayma birikirdi.
    COALESCE(SUM(h.planned_net_minutes), 0)                       AS net_minutes,
    ROUND(COALESCE(SUM(h.planned_net_minutes), 0) / 60.0, 2)      AS net_hours,
    ROUND(COALESCE(SUM(h.worked_net_minutes), 0) / 60.0, 2)       AS worked_net_hours,
    COALESCE(SUM(h.planned_hours), 0)                             AS gross_hours,
    ROUND(COALESCE(SUM(h.break_minutes), 0) / 60.0, 2)            AS break_hours,
    m.min_hours,
    GREATEST(0, m.min_hours - ROUND(COALESCE(SUM(h.worked_net_minutes), 0) / 60.0, 2))  AS missing_hours,
    -- Fazla mesai NET üzerinden: hedef de net olduğu için tutarlılık şart
    -- (Baran, 29.09). Brütle ölçülseydi molalar fazla mesai gibi görünürdü.
    GREATEST(0, ROUND(COALESCE(SUM(h.worked_net_minutes), 0) / 60.0, 2) - m.min_hours)  AS overtime_monthly,
    COALESCE(SUM(h.late_exit_hours), 0)                                                 AS overtime_late_exit,
    GREATEST(GREATEST(0, ROUND(COALESCE(SUM(h.worked_net_minutes), 0) / 60.0, 2) - m.min_hours),
             COALESCE(SUM(h.late_exit_hours), 0))                                       AS overtime_max
FROM schedule_drafts d
CROSS JOIN staff s
CROSS JOIN min_h m
LEFT JOIN v_assignment_hours h
       ON h.draft_id = d.id
      AND h.staff_id = s.id
      AND d.period @> h.work_date
WHERE s.is_active
   OR EXISTS (SELECT 1 FROM assignments a WHERE a.staff_id = s.id AND a.draft_id = d.id)
GROUP BY d.id, d.period, s.id, s.full_name, m.min_hours;

-- Adalet NET saatle ölçülür: iki kişinin brütü eşitken biri hep gece çalışıyorsa
-- (210 dk mola) fiilen daha az mesai yapmıştır. Brütle bakmak bunu gizlerdi.
CREATE VIEW v_fairness AS
WITH per_staff AS (
    SELECT
        mh.draft_id,
        mh.staff_id,
        mh.full_name,
        mh.net_hours,
        COUNT(h.assignment_id) FILTER (WHERE h.crosses_midnight)              AS night_count,
        COUNT(h.assignment_id) FILTER (WHERE EXTRACT(ISODOW FROM h.work_date) IN (6, 7)) AS weekend_count
    FROM v_monthly_hours mh
    LEFT JOIN v_assignment_hours h
           ON h.draft_id = mh.draft_id AND h.staff_id = mh.staff_id
          AND h.work_date >= mh.period_start AND h.work_date < mh.period_end
    GROUP BY mh.draft_id, mh.staff_id, mh.full_name, mh.net_hours
)
SELECT
    draft_id, staff_id, full_name, net_hours, night_count, weekend_count,
    ROUND(net_hours   - AVG(net_hours)   OVER (PARTITION BY draft_id), 1) AS hours_vs_avg,
    ROUND(night_count - AVG(night_count) OVER (PARTITION BY draft_id), 1) AS nights_vs_avg,
    RANK() OVER (PARTITION BY draft_id ORDER BY night_count DESC)         AS night_rank
FROM per_staff;
