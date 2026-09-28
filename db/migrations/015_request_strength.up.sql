-- 015_request_strength.up.sql
-- 28.09.2026: İstek DURUMU değil GÜCÜ. 'ONAYLANDI'/'BEKLEMEDE' bir onay akışını
-- anlatıyordu; asıl ayrım isteğin solver üzerindeki gücü:
--   KESIN    → katı kural, ihlal edilemez (eski ONAYLANDI)
--   MUMKUNSE → cezalı tercih, karşılanamazsa teşhiste görünür (eski BEKLEMEDE)
-- E-10'daki "onay beklemedeydi" metni bu yüzden yanlıştı.

ALTER TABLE availability_rules DROP CONSTRAINT ck_availability_rules_status;
ALTER TABLE availability_rules ALTER COLUMN status DROP DEFAULT;

UPDATE availability_rules SET status = CASE status
    WHEN 'ONAYLANDI' THEN 'KESIN'
    WHEN 'BEKLEMEDE' THEN 'MUMKUNSE'
    ELSE status END
WHERE status IN ('ONAYLANDI', 'BEKLEMEDE');

ALTER TABLE availability_rules ALTER COLUMN status SET DEFAULT 'MUMKUNSE';
ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_status CHECK (status IN ('MUMKUNSE', 'KESIN'));

COMMENT ON COLUMN availability_rules.status IS
    'İsteğin gücü — MUMKUNSE: cezalı tercih · KESIN: katı kural';
