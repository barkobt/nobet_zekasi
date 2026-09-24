-- 004_constraints_scope_source.up.sql
ALTER TABLE constraints
    ADD COLUMN scope  TEXT NOT NULL,
    ADD COLUMN source TEXT NOT NULL;

ALTER TABLE constraints
    ADD CONSTRAINT ck_constraints_scope
    CHECK (scope IN ('kisi', 'vardiya', 'gun', 'hafta', 'ay'));

ALTER TABLE constraints
    ADD CONSTRAINT ck_constraints_source
    CHECK (source IN ('yasal', 'kurumsal', 'tercih', 'belirsiz'));
