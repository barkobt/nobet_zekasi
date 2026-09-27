-- 013_assignment_source_referans.down.sql
-- 'referans' değeri kalkar; o satırlar 'manuel'e döner (ayrım kaybolur).

UPDATE assignments SET source = 'manuel' WHERE source = 'referans';

ALTER TABLE assignments DROP CONSTRAINT ck_assignments_source;

ALTER TABLE assignments
    ADD CONSTRAINT ck_assignments_source
    CHECK (source IN ('solver', 'manuel', 'onceki_ay'));
