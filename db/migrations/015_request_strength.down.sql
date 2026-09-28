-- 015_request_strength.down.sql
ALTER TABLE availability_rules DROP CONSTRAINT ck_availability_rules_status;
ALTER TABLE availability_rules ALTER COLUMN status DROP DEFAULT;

UPDATE availability_rules SET status = CASE status
    WHEN 'KESIN' THEN 'ONAYLANDI'
    WHEN 'MUMKUNSE' THEN 'BEKLEMEDE'
    ELSE status END
WHERE status IN ('KESIN', 'MUMKUNSE');

ALTER TABLE availability_rules ALTER COLUMN status SET DEFAULT 'BEKLEMEDE';
ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_status CHECK (status IN ('BEKLEMEDE', 'ONAYLANDI'));
