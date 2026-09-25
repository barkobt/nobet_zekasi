-- 002_shift_is_active.down.sql
ALTER TABLE shift_types
    DROP COLUMN is_active;
