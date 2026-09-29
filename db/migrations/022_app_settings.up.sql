-- 022_app_settings.up.sql
-- Kuruma özel, arayüzde görünen metinler. Bugün tek satır var: kurum adı.
--
-- NEDEN ayrı tablo: kurum adı Excel/PDF başlıklarında koda gömülüydü. Hastane
-- adının üründe geçmemesi yasal bir gereklilik; gömülü metin her değişiklikte
-- yeni dağıtım demek. Ayar olarak durursa planlayıcı kendi kurum adını yazar
-- ya da boş bırakır, kod hiç değişmez.
--
-- app_preferences'tan farkı: orası KULLANICI başına arayüz tercihi (ızgara açık
-- mı), burası kuruma ait TEK değer. Karıştırılmasın diye ayrı tablo.
--
-- value TEXT ve NOT NULL ama boş dizeye izin verilir: boş = "kurum adı hiç
-- yazılmasın" demektir, NULL ile aynı anlama gelen ikinci bir durum istemiyoruz.

CREATE TABLE app_settings (
    key         VARCHAR(64)  PRIMARY KEY,
    value       TEXT         NOT NULL,
    label       VARCHAR(120) NOT NULL,
    description TEXT,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE app_settings IS
    'Kuruma ait, arayüzden düzenlenebilir metin ayarları (örn. çıktı başlığındaki kurum adı).';
COMMENT ON COLUMN app_settings.value IS
    'Boş dize geçerlidir ve "bu metni hiç gösterme" anlamına gelir.';
