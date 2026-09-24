-- 003_constraints_weight_rule.down.sql
ALTER TABLE constraints
    RENAME CONSTRAINT uq_constraints_code TO uq_constraint_code;

ALTER TABLE constraints
    DROP CONSTRAINT ck_constraints_weight_by_type;

UPDATE constraints SET default_weight = 100 WHERE default_weight IS NULL;

ALTER TABLE constraints
    ALTER COLUMN default_weight SET DEFAULT 100,
    ALTER COLUMN default_weight SET NOT NULL;
