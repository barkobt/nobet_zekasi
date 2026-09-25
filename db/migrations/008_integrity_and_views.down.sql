-- 008_integrity_and_views.down.sql
-- Önce view'lar (tablolara bağımlılar), sonra kısıtlar, en son kolon.
-- v_fairness → v_monthly_hours → v_assignment_hours zincirine bağlı: en üstteki önce silinir.
DROP VIEW IF EXISTS v_daily_coverage;
DROP VIEW IF EXISTS v_fairness;
DROP VIEW IF EXISTS v_monthly_hours;
DROP VIEW IF EXISTS v_assignment_hours;
DROP VIEW IF EXISTS v_staff_conflict_pairs;

ALTER TABLE need_periods DROP CONSTRAINT IF EXISTS ck_need_periods_has_start;
ALTER TABLE absences     DROP CONSTRAINT IF EXISTS ck_absences_period_bounded;
ALTER TABLE contracts    DROP CONSTRAINT IF EXISTS ck_contracts_period_has_start;
ALTER TABLE contracts    DROP CONSTRAINT IF EXISTS ck_contracts_target_positive;
ALTER TABLE shift_types  DROP CONSTRAINT IF EXISTS ck_shift_types_duration;

ALTER TABLE staff DROP COLUMN IF EXISTS is_active;
