ALTER TABLE constraints DROP CONSTRAINT ck_constraints_source;
ALTER TABLE constraints DROP CONSTRAINT ck_constraints_scope;
ALTER TABLE constraints DROP COLUMN source;
ALTER TABLE constraints DROP COLUMN scope;