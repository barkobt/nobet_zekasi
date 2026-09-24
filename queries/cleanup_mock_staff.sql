-- queries/cleanup_mock_staff.sql
-- TEK SEFERLİK: Örnek (Notion) personeli sil. Sadece eski 007'yi çalıştırdıysan gerekli.
-- Gerçek 007'den ÖNCE çalıştır.
--
-- CASCADE sayesinde bu kişilerin sözleşmeleri, yetkinlikleri ve uyumsuzluk kayıtları da silinir.
-- Ataması olan kişi RESTRICT yüzünden silinemez → hata alırsan önce o taslağı sil.
-- "Muhammet Edem" iki listede de var: burada silinip gerçek seed'le doğru yetkinliklerle yeniden girilir.

BEGIN;

DELETE FROM staff
WHERE full_name IN (
    'Ayşe Korkmaz', 'Burak Yıldırım', 'Büşra Çetin', 'Ceren Bilgin', 'Deniz Aksoy',
    'Elif Şahin', 'Emre Kılıç', 'Furkan Aslan', 'Gizem Polat', 'Hakan Ersoy',
    'Kaan Yücel', 'Merve Toprak', 'Muhammet Edem', 'Onur Demirtaş', 'Selin Aydın',
    'Sıla Doğan', 'Tolga Şen', 'Zeynep Karaca', 'Eğitim Hemşiresi (örnek)'
);

SELECT count(*) AS kalan_personel FROM staff;   -- 0 beklenir

COMMIT;
