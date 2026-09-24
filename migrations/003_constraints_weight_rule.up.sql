-- 003_constraints_weight_rule.up.sql
ALTER TABLE constraints
    ALTER COLUMN default_weight DROP NOT NULL,
    ALTER COLUMN default_weight DROP DEFAULT;

ALTER TABLE constraints
    ADD CONSTRAINT ck_constraints_weight_by_type
    CHECK (
        (is_hard AND default_weight IS NULL)
        OR
        (NOT is_hard AND default_weight IS NOT NULL AND default_weight > 0)
    );

ALTER TABLE constraints
    RENAME CONSTRAINT uq_constraint_code TO uq_constraints_code;
