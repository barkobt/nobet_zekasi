-- 002_shift_is_active.up.sql
-- Vardiya tipini silmeden açıp kapatabilmek için

ALTER TABLE shift_types
    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE;