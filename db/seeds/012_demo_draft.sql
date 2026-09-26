-- seeds/012_demo_draft.sql
-- Demo için hazır bir "Ekim 2026" taslağı: referans hafta hedef aya döşenmiş,
-- stub ile çözülmüş gibi işaretlenmiş.
--
-- NEDEN SEED: sunumda taslak hazır dursun isteniyor. Elle oluşturulursa her Neon
-- kurulumunda kaybolur. Burada durunca rebuild.sh onu da kuruyor.
-- Döşeme mantığı solver/stub.py ile AYNI: hafta gününe göre eşleme.

BEGIN;

INSERT INTO schedule_drafts (unit_id, period, name)
SELECT id, daterange('2026-10-01', '2026-11-01', '[)'), 'Ekim 2026 çizelgesi'
FROM units
WHERE code = 'ACIL_SERVIS'
  AND NOT EXISTS (SELECT 1 FROM schedule_drafts WHERE name = 'Ekim 2026 çizelgesi');

-- Atamalar: referans haftanın her günü, hedef aydaki aynı hafta gününe.
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source)
SELECT h.id, r.staff_id, r.shift_type_id, g.gun, 'solver'
FROM schedule_drafts h
CROSS JOIN LATERAL generate_series(lower(h.period), upper(h.period) - 1, INTERVAL '1 day') AS g(gun)
JOIN (
    SELECT a.staff_id, a.shift_type_id, EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
    FROM assignments a
    JOIN schedule_drafts d ON d.id = a.draft_id
    WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
) r ON r.hafta_gunu = EXTRACT(ISODOW FROM g.gun)::int
WHERE h.name = 'Ekim 2026 çizelgesi'
ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING;

-- Görev rozetleri. staff_competencies filtresi ŞART: migration 010'un trigger'ı
-- solver kaynaklı atamaya yetkinliksiz görev yazılmasını hata olarak reddeder.
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT y.id, r.competency_id
FROM (
    SELECT a.id, a.staff_id, EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
    FROM assignments a
    JOIN schedule_drafts d ON d.id = a.draft_id
    WHERE d.name = 'Ekim 2026 çizelgesi'
) y
JOIN (
    SELECT a.staff_id, t.competency_id, EXTRACT(ISODOW FROM a.work_date)::int AS hafta_gunu
    FROM assignments a
    JOIN assignment_tasks t ON t.assignment_id = a.id
    JOIN schedule_drafts d  ON d.id = a.draft_id
    WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
) r ON r.staff_id = y.staff_id AND r.hafta_gunu = y.hafta_gunu
WHERE EXISTS (SELECT 1 FROM staff_competencies sc
              WHERE sc.staff_id = y.staff_id AND sc.competency_id = r.competency_id)
ON CONFLICT DO NOTHING;

-- Çalıştırma kaydı. params_snapshot'taki 'stub' arayüzün "Referans kopya
-- (solver değil)" etiketini göstermesini sağlar — gerçek çözüm sanılmasın.
INSERT INTO solver_runs (draft_id, status, finished_at, time_limit_seconds,
                         objective_value, params_snapshot)
SELECT d.id, 'FEASIBLE', CURRENT_TIMESTAMP, 60, 0,
       json_build_object('solver', 'stub', 'kaynak', 'seeds/012')::jsonb
FROM schedule_drafts d
WHERE d.name = 'Ekim 2026 çizelgesi'
  AND NOT EXISTS (SELECT 1 FROM solver_runs r WHERE r.draft_id = d.id);

-- Kapsama eksikleri teşhis olarak (E-10 dolu görünsün).
INSERT INTO solver_diagnostics (solver_run_id, severity, constraint_id, work_date, message, suggestion)
SELECT r.id, 'ihlal', ntr.constraint_id, cov.day,
       v.vardiya || ' ' || sl.slot || ': ' || cov.assigned || '/' || cov.required,
       'Gereken ' || cov.required || ' kişi, atanan ' || cov.assigned || '. '
         || 'İhtiyaç şablonundaki sayıyı gözden geçirin veya yetkin personel ekleyin.'
FROM solver_runs r
JOIN schedule_drafts d ON d.id = r.draft_id AND d.name = 'Ekim 2026 çizelgesi'
JOIN v_daily_coverage cov ON cov.draft_id = d.id AND cov.assigned < cov.required
JOIN (VALUES ('GUNDUZ','Gündüz'), ('GECE','Gece'), ('GUNDUZ_CMT','Gündüz (Cmt)'))
     AS v (kod, vardiya) ON v.kod = cov.shift_code
JOIN (VALUES ('GENEL','genel mevcut'), ('TRIYAJ','triyaj'), ('AMBULANS','ambulans'),
             ('GOZLEM','gözlem'), ('SAYIM','sayım yetkilisi'), ('SHIFT_YETKILISI','ekip lideri'))
     AS sl (kod, slot) ON sl.kod = cov.slot_code
JOIN need_periods np        ON np.valid_period @> cov.day
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
                           AND ntr.slot_code = cov.slot_code
JOIN shift_types st         ON st.id = ntr.shift_type_id AND st.code = cov.shift_code
WHERE NOT EXISTS (SELECT 1 FROM solver_diagnostics g WHERE g.solver_run_id = r.id);

COMMIT;
