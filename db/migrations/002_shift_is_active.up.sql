-- 002_shift_is_active.up.sql
ALTER TABLE shift_types
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;
