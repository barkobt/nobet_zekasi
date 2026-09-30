-- seeds/033_kagit_hafta_28eyl_04eki.sql
-- 30.09.2026: Kağıt haftalık çizelgenin (28.09–04.10.2026) veritabanına aktarımı.
-- Kaynak: Baran'ın yüklediği fotoğraf, elle okundu.
--
-- NE OLUYOR
--   * Tek taslak "Hafta 28 Eyl – 4 Eki 2026 (kağıt)", status='yayinlandi',
--     dönem [2026-09-28, 2026-10-05). Bu hafta İŞLENMİŞTİR: Ekim taslağı çözülürken
--     1–4 Ekim günleri bu çizelgeden kilitli olarak alınır, solver dokunmaz
--     (solver/model.py → _islenmis_gunleri_esitle).
--   * "Eylül 2026 (kağıt)" dönemi [08-31, 09-30) idi ve 28–29 Eylül'ü kapsıyordu.
--     O iki günün satırları kağıdın ESKİ bir sürümünden gelmişti; yeni fotoğraf
--     daha güncel. Eylül'ün dönemi [08-31, 09-28)'e çekilir, 28–29 satırları silinir
--     (ex_drafts_one_published iki yayının çakışmasına izin vermiyor).
--
-- OKUMA İLKELERİ (seeds/022 ve 028 ile aynı)
--   * Hİ (haftalık izin) ve boş hücre → atama yok.
--   * Yİ → yıllık izin (absences).
--   * GECE(01:00) → GECE_0100 (pasif vardiya, yalnız geçmiş kayıt).
--   * (ORY) → oryantasyon; ayrı vardiya değil, kişi zaten oryantasyonda.
--   * Yeşil → GOZLEM, pembe → AMBULANS. Rengi olmayan satır ROZETSİZ bırakılır
--     ("kağıtta görev belirtilmemiş"); triyaj VARSAYILMAZ (seeds/028'in dersi).
--   * Emre Baydilli 28.09 GECE turuncu (pembe + sarı üst üste) → AMBULANS sayıldı.
--   * Kağıt altındaki el yazısı notlar (Derya 03.10, Fatih/Merve 04.10) ve kuralla
--     çelişen hücreler (ör. Merve Armut 30.09 GECE) yöneticinin bu haftaya özel
--     kararıdır (Edem, 30.09): olduğu gibi aktarılır, kurala uydurulmaz.
--
-- Tekrar çalıştırılabilir: taslak adla aranır, satırlar ON CONFLICT ile korunur.

BEGIN;

-- 1) Eylül kağıdını 27 Eylül'de bitir, eski 28–29 satırlarını kaldır
DELETE FROM assignments a
USING schedule_drafts d
WHERE a.draft_id = d.id
  AND d.name = 'Eylül 2026 (kağıt)'
  AND a.work_date >= DATE '2026-09-28';

UPDATE schedule_drafts
   SET period = daterange('2026-08-31', '2026-09-28', '[)')
 WHERE name = 'Eylül 2026 (kağıt)'
   AND period <> daterange('2026-08-31', '2026-09-28', '[)');

-- 2) Haftanın taslağı
INSERT INTO schedule_drafts (unit_id, period, name, status, published_at)
SELECT id, daterange('2026-09-28', '2026-10-05', '[)'),
       'Hafta 28 Eyl – 4 Eki 2026 (kağıt)', 'yayinlandi', CURRENT_TIMESTAMP
FROM units WHERE code = 'ACIL_SERVIS'
  AND NOT EXISTS (SELECT 1 FROM schedule_drafts
                   WHERE name = 'Hafta 28 Eyl – 4 Eki 2026 (kağıt)');

-- 3) Atamalar
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source)
SELECT d.id, s.id, st.id, x.gun::date, 'referans'
FROM (VALUES
  -- Halit Güler
  ('2026-09-28','Halit Güler','GUNDUZ'), ('2026-09-29','Halit Güler','GUNDUZ'),
  ('2026-09-30','Halit Güler','GUNDUZ'), ('2026-10-01','Halit Güler','GUNDUZ'),
  ('2026-10-02','Halit Güler','GUNDUZ'), ('2026-10-03','Halit Güler','GUNDUZ'),
  -- Zehra Kutucu
  ('2026-09-28','Zehra Kutucu','GECE'),   ('2026-10-01','Zehra Kutucu','GUNDUZ'),
  ('2026-10-02','Zehra Kutucu','GUNDUZ'), ('2026-10-03','Zehra Kutucu','GECE'),
  ('2026-10-04','Zehra Kutucu','GECE'),
  -- Şükran Ünlü
  ('2026-09-28','Şükran Ünlü','GUNDUZ'), ('2026-09-29','Şükran Ünlü','GUNDUZ'),
  ('2026-09-30','Şükran Ünlü','GUNDUZ'), ('2026-10-01','Şükran Ünlü','GUNDUZ'),
  ('2026-10-02','Şükran Ünlü','GUNDUZ'),
  -- Mediha Aydoğan
  ('2026-09-28','Mediha Aydoğan','GECE'),   ('2026-09-29','Mediha Aydoğan','GECE'),
  ('2026-10-02','Mediha Aydoğan','GUNDUZ'), ('2026-10-03','Mediha Aydoğan','GECE'),
  -- Engin Sümer
  ('2026-09-28','Engin Sümer','GUNDUZ'), ('2026-09-29','Engin Sümer','GECE'),
  ('2026-09-30','Engin Sümer','GECE'),   ('2026-10-03','Engin Sümer','GUNDUZ'),
  ('2026-10-04','Engin Sümer','GUNDUZ'),
  -- Birol Karaca
  ('2026-09-28','Birol Karaca','GUNDUZ'), ('2026-09-29','Birol Karaca','GUNDUZ'),
  ('2026-09-30','Birol Karaca','GUNDUZ'), ('2026-10-01','Birol Karaca','GECE'),
  ('2026-10-02','Birol Karaca','GECE'),
  -- Fatih Sırcan
  ('2026-09-29','Fatih Sırcan','GECE_0100'), ('2026-09-30','Fatih Sırcan','GECE'),
  ('2026-10-03','Fatih Sırcan','GUNDUZ'),    ('2026-10-04','Fatih Sırcan','GECE'),
  -- Serpil Demir (28–30 yıllık izin, aşağıda)
  ('2026-10-01','Serpil Demir','GUNDUZ'), ('2026-10-02','Serpil Demir','GUNDUZ'),
  ('2026-10-04','Serpil Demir','GUNDUZ'),
  -- Eda Karakuş
  ('2026-09-30','Eda Karakuş','GUNDUZ'), ('2026-10-01','Eda Karakuş','GECE'),
  ('2026-10-02','Eda Karakuş','GECE'),
  -- Havva Abravcı
  ('2026-09-28','Havva Abravcı','GECE_0100'), ('2026-09-29','Havva Abravcı','GECE'),
  ('2026-10-03','Havva Abravcı','GUNDUZ'),    ('2026-10-04','Havva Abravcı','GECE'),
  -- Sevda Koç
  ('2026-09-28','Sevda Koç','GUNDUZ'), ('2026-09-29','Sevda Koç','GUNDUZ'),
  ('2026-09-30','Sevda Koç','GUNDUZ'), ('2026-10-01','Sevda Koç','GUNDUZ'),
  ('2026-10-04','Sevda Koç','GUNDUZ'),
  -- Muhammet Edem
  ('2026-09-28','Muhammet Edem','GUNDUZ'),    ('2026-09-29','Muhammet Edem','GUNDUZ'),
  ('2026-09-30','Muhammet Edem','GUNDUZ'),    ('2026-10-01','Muhammet Edem','GECE_0100'),
  ('2026-10-02','Muhammet Edem','GECE'),      ('2026-10-04','Muhammet Edem','GUNDUZ'),
  -- Kader Can
  ('2026-09-30','Kader Can','GECE'),   ('2026-10-01','Kader Can','GECE'),
  ('2026-10-03','Kader Can','GUNDUZ'), ('2026-10-04','Kader Can','GECE'),
  -- Emre Baydilli
  ('2026-09-28','Emre Baydilli','GECE'),   ('2026-09-30','Emre Baydilli','GUNDUZ'),
  ('2026-10-01','Emre Baydilli','GUNDUZ'), ('2026-10-02','Emre Baydilli','GECE'),
  ('2026-10-04','Emre Baydilli','GECE_0100'),
  -- Sıla Öner
  ('2026-09-29','Sıla Öner','GUNDUZ'),    ('2026-09-30','Sıla Öner','GECE_0100'),
  ('2026-10-01','Sıla Öner','GECE'),      ('2026-10-03','Sıla Öner','GECE'),
  -- Derya Torun
  ('2026-09-30','Derya Torun','GECE'), ('2026-10-01','Derya Torun','GECE'),
  ('2026-10-03','Derya Torun','GECE'),
  -- Merve Armut
  ('2026-09-28','Merve Armut','GUNDUZ'), ('2026-09-29','Merve Armut','GUNDUZ'),
  ('2026-09-30','Merve Armut','GECE'),   ('2026-10-02','Merve Armut','GUNDUZ'),
  ('2026-10-03','Merve Armut','GUNDUZ'),
  -- Murat Sığınç
  ('2026-09-28','Murat Sığınç','GECE'),   ('2026-09-29','Murat Sığınç','GECE'),
  ('2026-10-01','Murat Sığınç','GUNDUZ'), ('2026-10-02','Murat Sığınç','GECE'),
  ('2026-10-03','Murat Sığınç','GECE'),
  -- Ayşe Kartal (oryantasyon)
  ('2026-09-28','Ayşe Kartal','GECE'),   ('2026-09-29','Ayşe Kartal','GECE'),
  ('2026-10-02','Ayşe Kartal','GUNDUZ'), ('2026-10-03','Ayşe Kartal','GUNDUZ'),
  ('2026-10-04','Ayşe Kartal','GECE'),
  -- Güven Göl (oryantasyon)
  ('2026-09-28','Güven Göl','GUNDUZ'), ('2026-09-29','Güven Göl','GUNDUZ'),
  ('2026-09-30','Güven Göl','GUNDUZ'), ('2026-10-01','Güven Göl','GUNDUZ'),
  ('2026-10-02','Güven Göl','GUNDUZ'), ('2026-10-03','Güven Göl','GUNDUZ')
) AS x (gun, ad, vardiya)
JOIN schedule_drafts d ON d.name = 'Hafta 28 Eyl – 4 Eki 2026 (kağıt)'
JOIN staff s           ON s.full_name = x.ad
JOIN shift_types st    ON st.code = x.vardiya
ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING;

-- 4) Rozetler: yeşil = GOZLEM, pembe = AMBULANS
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT a.id, c.id
FROM (VALUES
  ('2026-10-01','Zehra Kutucu','GOZLEM'),   ('2026-10-02','Zehra Kutucu','GOZLEM'),
  ('2026-09-29','Şükran Ünlü','GOZLEM'),    ('2026-10-02','Şükran Ünlü','AMBULANS'),
  ('2026-09-28','Mediha Aydoğan','GOZLEM'), ('2026-09-29','Mediha Aydoğan','GOZLEM'),
  ('2026-10-02','Mediha Aydoğan','GOZLEM'), ('2026-10-03','Mediha Aydoğan','GOZLEM'),
  ('2026-09-28','Engin Sümer','AMBULANS'),  ('2026-09-30','Engin Sümer','AMBULANS'),
  ('2026-10-04','Engin Sümer','AMBULANS'),
  ('2026-09-28','Birol Karaca','GOZLEM'),   ('2026-09-30','Birol Karaca','GOZLEM'),
  ('2026-09-30','Fatih Sırcan','GOZLEM'),   ('2026-10-03','Fatih Sırcan','GOZLEM'),
  ('2026-10-04','Fatih Sırcan','AMBULANS'),
  ('2026-09-30','Eda Karakuş','GOZLEM'),    ('2026-10-01','Eda Karakuş','GOZLEM'),
  ('2026-10-02','Eda Karakuş','GOZLEM'),
  ('2026-09-29','Havva Abravcı','AMBULANS'), ('2026-10-03','Havva Abravcı','AMBULANS'),
  ('2026-10-04','Havva Abravcı','GOZLEM'),
  ('2026-09-29','Sevda Koç','GOZLEM'),      ('2026-10-01','Sevda Koç','GOZLEM'),
  ('2026-10-04','Sevda Koç','GOZLEM'),
  ('2026-09-28','Muhammet Edem','AMBULANS'), ('2026-09-29','Muhammet Edem','AMBULANS'),
  ('2026-09-30','Muhammet Edem','AMBULANS'), ('2026-10-02','Muhammet Edem','GOZLEM'),
  ('2026-10-04','Muhammet Edem','AMBULANS'),
  ('2026-09-30','Kader Can','AMBULANS'),    ('2026-10-01','Kader Can','AMBULANS'),
  ('2026-10-03','Kader Can','AMBULANS'),    ('2026-10-04','Kader Can','AMBULANS'),
  ('2026-09-28','Emre Baydilli','AMBULANS'), ('2026-09-30','Emre Baydilli','AMBULANS'),
  ('2026-10-01','Emre Baydilli','AMBULANS'), ('2026-10-02','Emre Baydilli','AMBULANS'),
  ('2026-09-29','Sıla Öner','AMBULANS'),    ('2026-10-01','Sıla Öner','AMBULANS'),
  ('2026-10-03','Sıla Öner','AMBULANS'),
  ('2026-09-30','Derya Torun','GOZLEM'),    ('2026-10-01','Derya Torun','GOZLEM'),
  ('2026-10-03','Derya Torun','GOZLEM'),
  ('2026-09-28','Murat Sığınç','AMBULANS'), ('2026-09-29','Murat Sığınç','AMBULANS'),
  ('2026-10-01','Murat Sığınç','AMBULANS'), ('2026-10-02','Murat Sığınç','AMBULANS'),
  ('2026-10-03','Murat Sığınç','AMBULANS'),
  ('2026-10-02','Ayşe Kartal','AMBULANS')
) AS x (gun, ad, gorev)
JOIN schedule_drafts d ON d.name = 'Hafta 28 Eyl – 4 Eki 2026 (kağıt)'
JOIN staff s        ON s.full_name = x.ad
JOIN assignments a  ON a.draft_id = d.id AND a.staff_id = s.id AND a.work_date = x.gun::date
JOIN competencies c ON c.code = x.gorev
ON CONFLICT DO NOTHING;

-- 5) Yıllık izin: Serpil Demir 28–30 Eylül. seeds/022 28–29'u yazmıştı; aralık
--    30 Eylül'ü de kapsayacak şekilde tek satıra genişletilir.
DELETE FROM absences ab
USING staff s
WHERE ab.staff_id = s.id AND s.full_name = 'Serpil Demir'
  AND ab.period = daterange('2026-09-28', '2026-09-29', '[]');

INSERT INTO absences (staff_id, period, absence_type, note)
SELECT s.id, daterange('2026-09-28', '2026-09-30', '[]'), 'yillik_izin',
       'Kağıt hafta 28.09–04.10'
FROM staff s
WHERE s.full_name = 'Serpil Demir'
  AND NOT EXISTS (SELECT 1 FROM absences ab WHERE ab.staff_id = s.id
                    AND ab.period && daterange('2026-09-28', '2026-09-30', '[]'));

COMMIT;
