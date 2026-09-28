-- 014_request_status.down.sql
ALTER TABLE availability_rules DROP CONSTRAINT ck_availability_rules_type;

ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_type
    CHECK (rule_type IN ('off_talebi', 'acilis_tercihi', 'kapanis_tercihi'));

ALTER TABLE availability_rules DROP CONSTRAINT ck_availability_rules_status;
ALTER TABLE availability_rules DROP COLUMN status;
