-- 025_roles_display_group.sql
-- Rol gruplarının değerleri (migration 019 kolonları ekledi, veri burada).
-- Web'deki sabit GRUPLAR dizisiyle aynı bölümleme; artık tek kaynak veritabanı.

BEGIN;

UPDATE roles SET display_group = v.grup, sort_order = v.sira
  FROM (VALUES
          ('sorumlu_hemsire', 'Sorumlu & Eğitim',  10),
          ('egitim_hemsire',  'Sorumlu & Eğitim',  20),
          ('shift_yetkilisi', 'Ekip Liderleri',    30),
          ('hemsire',         'Hemşireler',        40),
          ('att_paramedik',   'Hemşireler',        50)
       ) AS v(kod, grup, sira)
 WHERE roles.code = v.kod;

COMMIT;
