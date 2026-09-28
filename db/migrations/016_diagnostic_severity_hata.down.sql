-- 016_diagnostic_severity_hata.down.sql
DELETE FROM solver_diagnostics WHERE severity = 'hata';

ALTER TABLE solver_diagnostics DROP CONSTRAINT ck_diag_severity;

ALTER TABLE solver_diagnostics
    ADD CONSTRAINT ck_diag_severity
    CHECK (severity IN ('cakisma', 'ihlal', 'uyari'));
