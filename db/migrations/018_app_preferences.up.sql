-- 018_app_preferences.up.sql
-- Kullanıcının arayüz tercihleri. localStorage KULLANILMIYOR: tercih sunucuda
-- durmalı ki başka bir tarayıcıdan ya da sunum makinesinden aynı görünüm açılsın.
--
-- Sistemde henüz kullanıcı kimliği yok (tek paylaşılan parola). O yüzden anahtar
-- serbest metin: bugün 'demo'. Kimlik geldiğinde staff_id'ye bağlanır.

CREATE TABLE app_preferences (
    user_key   VARCHAR(64)  NOT NULL,
    pref_key   VARCHAR(64)  NOT NULL,
    value      JSONB        NOT NULL,
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (user_key, pref_key)
);

COMMENT ON TABLE app_preferences IS
    'Kullanıcı başına arayüz tercihleri (örn. çizelgede "Detayları göster" açık mı).';
