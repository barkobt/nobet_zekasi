-- 029_kurum_adi.sql
-- Excel/PDF başlıklarında görünen kurum adı.
--
-- NEDEN nötr bir değer: hastane kendi adının, logosunun ve hiçbir marka
-- öğesinin üründe geçmemesini istedi (29.09.2026). Kurum adı eskiden
-- api/app/routers/export.py içinde gömülüydü; buraya taşındı ve nötrlendi.
--
-- Planlayıcı Ayarlar ekranından değiştirebilir. Boş bırakılırsa çıktı
-- başlığında kurum satırı hiç yazılmaz.

INSERT INTO app_settings (key, value, label, description)
VALUES (
    'org_name',
    'Acil Servis',
    'Kurum adı',
    'Excel ve PDF çıktılarının başlığında birim adının önünde görünür. Boş bırakılırsa hiç yazılmaz.'
)
ON CONFLICT (key) DO NOTHING;
