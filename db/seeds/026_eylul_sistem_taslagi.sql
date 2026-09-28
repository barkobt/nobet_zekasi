-- 026_eylul_sistem_taslagi.sql
-- Karşılaştırma için "Eylül 2026 — sistem" taslağı.
--
-- Kağıt Eylül ile AYNI dönem ve AYNI izinler; fark yalnızca çizelgeyi kimin
-- kurduğu. Atama KOPYALANMAZ: solver sıfırdan çözecek, ipucu da olmayacak —
-- yoksa karşılaştırma "kağıdı ne kadar iyi taklit etti" olurdu.

BEGIN;

INSERT INTO schedule_drafts (unit_id, name, period, status)
SELECT u.id,
       'Eylül 2026 — sistem',
       daterange(DATE '2026-08-31', DATE '2026-09-30', '[)'),
       'taslak'
FROM units u
WHERE u.code = 'ACIL_SERVIS'
  AND NOT EXISTS (SELECT 1 FROM schedule_drafts WHERE name = 'Eylül 2026 — sistem');

COMMIT;
