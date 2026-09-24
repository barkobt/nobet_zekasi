-- seeds/009_reference_week_2026_09_21.sql
-- Elle hazırlanmış GERÇEK çizelge: 21–27 Eylül 2026 (kağıt çizelgenin birebir aktarımı).
-- Yol Haritası Adım 10: "En az bir haftalık elle yazılmış geçerli çizelge gir."
-- İki işe yarar: 1) Kurallarımız gerçeği doğru anlatıyor mu? 2) Solver'ın sonucunu neyle kıyaslayacağız?
--
-- Hücre kodu (kağıttaki gibi):  D = GÜNDÜZ   N = GECE   boş = çalışmıyor (Hİ veya dinlenme)
-- Kağıttaki GECE(01:00) hücreleri aktarılmadı (24.09 kararı: kısa gece modelde yok).
-- Merve Armut'un 2 gecesi ve Pazar gündüzün 4 kişi olması zorunluluktan; olduğu gibi aktarıldı.
-- Görev eki (kağıttaki renkler): /a = pembe (ambulans)   /g = sarı (gözlem)
--
-- KALIP: Kağıt ızgarası (kişi × 7 gün) staging'e → CROSS JOIN LATERAL ile (kişi, gün) satırlarına açılır.

BEGIN;

-- 1) Taslak başlığı: Eylül ayının yayınlanmış çizelgesi (elle hazırlanan)
INSERT INTO schedule_drafts (unit_id, month_start, name, status, published_at)
SELECT id, '2026-09-01', 'Referans: elle hazırlanan 21-27 Eylül', 'yayinlandi', '2026-09-20 18:00+03'
FROM units
WHERE code = 'ACIL_SERVIS'
  AND NOT EXISTS (SELECT 1 FROM schedule_drafts WHERE name = 'Referans: elle hazırlanan 21-27 Eylül');

-- 2) Kağıt ızgarası
CREATE TEMP TABLE tmp_grid (
    full_name TEXT, pzt TEXT, sal TEXT, car TEXT, per TEXT, cum TEXT, cmt TEXT, paz TEXT
) ON COMMIT DROP;

INSERT INTO tmp_grid VALUES
--  ad soyad          Pzt 21   Salı 22  Çar 23   Per 24   Cuma 25  Cmt 26   Paz 27
('Halit Güler',     'D',     'D',     'D',     'D',     'D',     'D',     ''),
('Zehra Kutucu',    'N/g',   'N/g',   '',      '',      'D/g',   'D',     'N'),
('Şükran Ünlü',     'D',     'D',     'D/a',   'D',     'D/a',   '',      ''),
('Mediha Aydoğan',  '',      '',      'N/g',   'N/g',   '',      'D/g',   'D/g'),
('Engin Sümer',     'D/a',   'D/a',   'N',     'N',     '',      '',      'D'),
('Birol Karaca',    'N',     'N',     '',      '',      'N',     '',      ''),
('Fatih Sırcan',    'N',     '',      '',      '',      'N/a',   'N',     ''),
('Serpil Demir',    'D',     'D',     'D',     'D',     '',      'D',     ''),
('Eda Karakuş',     '',      'D/g',   'D/g',   'D/g',   '',      'N/g',   'N/g'),
('Havva Abravcı',   '',      'D/a',   'N/g',   'N/a',   '',      'D/a',   'D/a'),
('Sevda Koç',       'D/g',   'D/g',   'D/g',   'D/g',   'D/g',   'D',     ''),
('Muhammet Edem',   'N/g',   'N/g',   '',      'N/g',   'N/g',   '',      ''),
('Kader Can',       '',      '',      'N/a',   '',      '',      'N/a',   'N/a'),
('Emre Baydilli',   '',      '',      'D/a',   'D/a',   'N/a',   'N/a',   ''),
('Sıla Öner',       '',      '',      '',      'N/a',   '',      'N/g',   'N/a'),
('Derya Torun',     '',      'N',     '',      '',      'D',     'D/g',   'N/g'),
('Merve Armut',     'N',     '',      'D',     'D',     'N',     '',      ''),
('Murat Sığınç',    'D/a',   'N/a',   'N/a',   '',      'D/a',   '',      'D/a'),
('Ayşe Kartal',     'D',     'D',     'D',     'D',     'D',     '',      'D'),
('Güven Göl',       'D',     'D',     'D',     'D',     'D',     'D/a',   '');

-- 3) Izgarayı (kişi, gün, hücre) satırlarına aç → boş hücreleri at → vardiya ve görevi ayır
CREATE TEMP TABLE tmp_cells ON COMMIT DROP AS
SELECT g.full_name,
       d.work_date,
       split_part(d.cell, '/', 1) AS shift_letter,
       NULLIF(split_part(d.cell, '/', 2), '') AS task_letter
FROM tmp_grid g
CROSS JOIN LATERAL (VALUES
    (DATE '2026-09-21', g.pzt), (DATE '2026-09-22', g.sal), (DATE '2026-09-23', g.car),
    (DATE '2026-09-24', g.per), (DATE '2026-09-25', g.cum), (DATE '2026-09-26', g.cmt),
    (DATE '2026-09-27', g.paz)
) AS d (work_date, cell)
WHERE d.cell <> '';

-- 4) Atamalar. Harf → vardiya kodu çevirisi küçük bir VALUES sözlüğüyle.
INSERT INTO assignments (draft_id, staff_id, shift_type_id, work_date, source)
SELECT dr.id, s.id, st.id, c.work_date, 'manuel'
FROM tmp_cells c
JOIN (VALUES ('D', 'GUNDUZ'), ('N', 'GECE')) AS m (letter, shift_code)
     ON m.letter = c.shift_letter
JOIN staff s            ON s.full_name = c.full_name
JOIN shift_types st     ON st.code = m.shift_code
JOIN schedule_drafts dr ON dr.name = 'Referans: elle hazırlanan 21-27 Eylül'
ON CONFLICT (draft_id, staff_id, work_date) DO NOTHING;

-- 5) Görevler (renkler)
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT a.id, comp.id
FROM tmp_cells c
JOIN (VALUES ('a', 'AMBULANS'), ('g', 'GOZLEM')) AS m (letter, competency_code)
     ON m.letter = c.task_letter
JOIN staff s            ON s.full_name = c.full_name
JOIN schedule_drafts dr ON dr.name = 'Referans: elle hazırlanan 21-27 Eylül'
JOIN assignments a      ON a.draft_id = dr.id AND a.staff_id = s.id AND a.work_date = c.work_date
JOIN competencies comp  ON comp.code = m.competency_code
ON CONFLICT (assignment_id, competency_id) DO NOTHING;

COMMIT;
