-- seeds/035_mesai_dengesi.sql
-- O-010 Mesai dengesi (Baran, 30.09.2026).
--
-- "Ek mesai en aza insin, ama oluyorsa — ki olacak — eşit dağıtılsın."
-- O-001 TOPLAM mesaiyi azaltır; kimin mesai yaptığına bakmaz. Gece molası 3,5 sa
-- olduğu için gece sayısı brütü hızlı büyütür: 2 gecelik hafta 6,5 sa, 4 gecelik
-- hafta 16,5 sa mesai. Ölçüm (Ekim, 30.09): kişi başı aylık mesai 19,5 ile 51 sa.
-- Bu kural kişilerin aylık mesaisini ORTALAMAYA yaklaştırır (Pazar'ı aya düşen
-- haftalar; kağıttan gelen işlenmiş hafta da sayılır, solver kalan haftalarda telafi eder).
--
-- Yumuşak. Zorunlu yapılırsa en çok ve en az mesai arası 10 saati geçmez
-- (parametre max_monthly_gap_hours).
--
-- Tekrar çalıştırılabilir.

BEGIN;

INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source) VALUES
    ('overtime_fairness',
     'Mesai dengesi',
     'Fazla mesai kaçınılmazsa kişiler arasında eşit dağılır: herkesin aylık mesaisi '
     'ortalamaya yakın olur. Mesai = haftalık brüt 51 sa üstü (O-001).',
     FALSE, 200, 'ay', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

UPDATE constraints SET catalog_code = 'O-010'
 WHERE code = 'overtime_fairness' AND catalog_code IS NULL;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, 'max_monthly_gap_hours', 10,
       'Zorunlu yapılırsa: en çok ve en az aylık mesai arasındaki en büyük fark (saat)'
FROM constraints c WHERE c.code = 'overtime_fairness'
ON CONFLICT (constraint_id, param_key) DO NOTHING;

COMMIT;
