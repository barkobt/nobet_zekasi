-- 002_shift_is_active.down.sql
-- up'ın tersi

ALTER TABLE shift_types
    DROP COLUMN is_active;