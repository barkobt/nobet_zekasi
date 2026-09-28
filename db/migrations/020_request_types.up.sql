-- 020_request_types.up.sql
-- Eski istek türlerini (off_talebi, acilis_tercihi, kapanis_tercihi) kaldırır.
--
-- Bu türler Orquest'ten devralınmış adlardı; sahada karşılıkları yok. Kullanılan
-- üçü BOS_GUN / SADECE_GUNDUZ / SADECE_GECE (migration 014 eklemişti) ve güç
-- ayrımı status kolonunda (migration 015: KESIN / MUMKUNSE).
--
-- UPDATE burada, seed'de değil: CHECK daraltılmadan önce satırların dönüşmesi
-- ŞART, yoksa constraint eklenemez. Veri üretmiyor, mevcut değeri çeviriyor.

UPDATE availability_rules
   SET rule_type = 'BOS_GUN'
 WHERE rule_type IN ('off_talebi', 'acilis_tercihi', 'kapanis_tercihi');

ALTER TABLE availability_rules DROP CONSTRAINT IF EXISTS ck_availability_rules_type;
ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_type
    CHECK (rule_type IN ('BOS_GUN', 'SADECE_GUNDUZ', 'SADECE_GECE'));
