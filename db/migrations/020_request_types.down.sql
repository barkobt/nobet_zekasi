ALTER TABLE availability_rules DROP CONSTRAINT IF EXISTS ck_availability_rules_type;
ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_type
    CHECK (rule_type IN ('BOS_GUN', 'SADECE_GUNDUZ', 'SADECE_GECE',
                         'off_talebi', 'acilis_tercihi', 'kapanis_tercihi'));
