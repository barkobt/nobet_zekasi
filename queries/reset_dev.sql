-- queries/reset_dev.sql
-- SADECE GELİŞTİRME İÇİN: public şemasındaki HER ŞEYİ siler (tablolar, view'lar, veri, uzantılar).
-- Gerçek veri girildikten sonra (canlıya geçince) bir daha KULLANILMAZ; o zaman sadece yeni migration eklenir.
--
-- Önce doğru yerde olduğunu doğrula. Bu iki satırın sonucu nobet_zekasi ve bizim tablolarımız olmalı:
SELECT current_database();
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY 1;

-- Sonra sıfırla:
DROP SCHEMA public CASCADE;   -- şemayı ve içindeki her şeyi siler (CASCADE = bağımlılarıyla birlikte)
CREATE SCHEMA public;         -- boş şemayı geri açar
