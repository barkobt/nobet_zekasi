-- 016_diagnostic_severity_hata.up.sql
-- 28.09.2026: solver_diagnostics.severity'ye 'hata' değeri.
--
-- NEDEN: her çözümün sonunda bağımsız kontrolcü (solver/validate.py) koşuyor.
-- KATI bir kural ihlal edilmişse bu bir model hatasıdır — kadro yetmediği için
-- eksik kalan bir slottan ('ihlal') kategorik olarak farklıdır ve E-10'da en
-- üstte, ayrı bir seviyede görünmelidir.
--
-- Bu değer nasıl doğdu: C-009'un "ambulans sonrası alanda kalan" kuralı bir
-- bağlantı değişikliğinde sessizce kurulmaz oldu ve haftalarca fark edilmedi.
-- Artık sessizce kaybolan bir kural ilk koşuda kendini gösterir.

ALTER TABLE solver_diagnostics DROP CONSTRAINT ck_diag_severity;

ALTER TABLE solver_diagnostics
    ADD CONSTRAINT ck_diag_severity
    CHECK (severity IN ('cakisma', 'ihlal', 'uyari', 'hata'));

COMMENT ON COLUMN solver_diagnostics.severity IS
    'hata: kontrolcünün bulduğu KATI kural ihlali (model hatası) · '
    'ihlal: gevşetilebilir kuralın karşılanamaması · cakisma · uyari';
