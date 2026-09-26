-- seeds/011_triage_observation_model.sql
-- 26.09.2026 saha kararlarının VERİ tarafı. Tekrar çalıştırılabilir.

BEGIN;

---------------------------------------------------------------------------
-- 1) C-009 tek kurala çevrildi
---------------------------------------------------------------------------
-- Eski hali TAVAN olarak yazılmıştı ("ambulansa gidenlerin en fazla 1'i gözlemden").
-- Gözlemde 2 kişi varken bu "gözlemde en az 1 kalsın" ile aynı şeydi, ama TRİYAJ
-- tarafını hiç kapsamıyordu: 25 Eylül Cuma gündüz ambulansın ikisi de triyajdan
-- çıkıyor, kural ihlal edilmiyor ama triyajda kimse kalmıyordu.
-- Yeni hali TABAN: iki alan için de simetrik, şablon sayıları değişse de geçerli.
-- UPDATE ile aynı satır güncelleniyor → id korunuyor, need_template_rows bağları
-- ve katalog kodu C-009 yerinde kalıyor.
UPDATE constraints
SET code        = 'min_remaining_after_ambulance',
    name        = 'Ambulans sonrası asgari kalan',
    description = 'Ambulansa çıkanlar düşüldükten sonra triyajda en az 1, gözlemde en az 1 '
                  'kişi kalmalı. Ambulans dönüşlü görevdir; gidenler kendi alanlarının '
                  'sayısından düşmez, yalnızca "kalan" hesabına girmez.'
WHERE code = 'ambulance_observation_limit';

DELETE FROM constraint_params
WHERE param_key = 'max_ambulance_from_observation'
  AND constraint_id = (SELECT id FROM constraints WHERE code = 'min_remaining_after_ambulance');

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, p.anahtar, p.deger, p.aciklama
FROM constraints c
CROSS JOIN (VALUES
    ('min_remaining_triage',      1, 'Ambulans çıktıktan sonra triyajda kalması gereken en az kişi'),
    ('min_remaining_observation', 1, 'Ambulans çıktıktan sonra gözlemde kalması gereken en az kişi')
) AS p (anahtar, deger, aciklama)
WHERE c.code = 'min_remaining_after_ambulance'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

---------------------------------------------------------------------------
-- 2) Yeni kural: her çalışan ya triyajda ya gözlemde
---------------------------------------------------------------------------
-- Katalogda karşılığı yok (Notion'dan sonra netleşti) → catalog_code NULL.
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source)
VALUES ('all_crew_triage_or_observation', 'Her çalışan triyaj veya gözlemde',
        'Vardiyadaki her çalışan (sorumlu hemşire ve oryantasyondakiler hariç) ya triyaj '
        'ya gözlem görevindedir. İkisi aynı kişide olamaz; gözlemde değilse triyajdadır.',
        TRUE, NULL, 'vardiya', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

---------------------------------------------------------------------------
-- 3) Referans haftanın triyaj/gözlem rozetlerini kuraldan türet
---------------------------------------------------------------------------
-- Kağıt çizelgede yalnız ambulans (pembe) ve gözlem (sarı) renkleri vardı; triyaj
-- yazılmamıştı. Kural "gözlemde değilse triyajdadır" dediği için rozetler türetilebilir.
-- seeds/009 (kağıdın birebir aktarımı) DEĞİŞTİRİLMİYOR; bu dosya ayrı durur ve geri alınabilir.
--
-- Sıra önemli: önce TRI (yetkini olanlara), sonra kalanlara GÖZ.
-- Her ikisinin de yetkinliği yoksa hiçbir şey yazılmaz — queries/checks.sql'de listelenir.

-- 3a) Rozetsiz kalanlardan TRIYAJ yetkini olanlara TRI
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT a.id, c.id
FROM assignments a
JOIN staff s        ON s.id  = a.staff_id
JOIN roles ro       ON ro.id = s.role_id
JOIN schedule_drafts d ON d.id = a.draft_id
JOIN competencies c ON c.code = 'TRIYAJ'
WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
  AND NOT s.is_orientation
  AND ro.code <> 'sorumlu_hemsire'
  AND NOT EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies g ON g.id = t.competency_id
                  WHERE t.assignment_id = a.id AND g.code IN ('TRIYAJ', 'GOZLEM'))
  AND EXISTS (SELECT 1 FROM staff_competencies sc
              WHERE sc.staff_id = a.staff_id AND sc.competency_id = c.id)
ON CONFLICT DO NOTHING;

-- 3b) Hâlâ rozetsiz kalanlardan GOZLEM yetkini olanlara GÖZ
--     (Derya Torun 22 Eyl gece ve 25 Eyl gündüz: triyaj yetkinliği yok, gözlem var)
INSERT INTO assignment_tasks (assignment_id, competency_id)
SELECT a.id, c.id
FROM assignments a
JOIN staff s        ON s.id  = a.staff_id
JOIN roles ro       ON ro.id = s.role_id
JOIN schedule_drafts d ON d.id = a.draft_id
JOIN competencies c ON c.code = 'GOZLEM'
WHERE d.name = 'Referans: elle hazırlanan 21-27 Eylül'
  AND NOT s.is_orientation
  AND ro.code <> 'sorumlu_hemsire'
  AND NOT EXISTS (SELECT 1 FROM assignment_tasks t JOIN competencies g ON g.id = t.competency_id
                  WHERE t.assignment_id = a.id AND g.code IN ('TRIYAJ', 'GOZLEM'))
  AND EXISTS (SELECT 1 FROM staff_competencies sc
              WHERE sc.staff_id = a.staff_id AND sc.competency_id = c.id)
ON CONFLICT DO NOTHING;

COMMIT;
