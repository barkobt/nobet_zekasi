-- seeds/034_calisma_suresi_kurallari.sql
-- Çalışma süresi, izin ve mesai kuralları. Edem + Baran kararları, 30.09.2026.
--
-- Hepsi VERİ: sayılar Kural Seti ekranından (E-03) değiştirilir, deploy gerekmez.
-- Mola süreleri zaten Vardiya Tanımları'nda (E-01, shift_types.break_minutes).
--
--   NET  = vardiya süresi − mola   (gündüz 8 sa 10 dk, gece 11 sa)
--   BRÜT = vardiya süresi          (gündüz 9,5 sa,     gece 14,5 sa)
--
--   C-026  Haftalık yasal asgari   net 45 sa / Pzt–Paz hafta          KATI · yasal
--   C-027  Aylık yasal asgari      net 180 sa / takvim ayı            KATI · yasal
--   C-004  Aylık hedef             net 200 sa — DEĞİŞMEDİ (hedef, yasal alt sınır değil)
--   C-028  Haftalık çalışma günü   en az 5 gün çalışır, en fazla 2 gün izin   KATI
--   C-025  Karma hafta             gündüz+gece personelde ≥1 gündüz + ≥1 gece  artık KATI
--   O-001  Fazla mesai             haftalık BRÜT 51 sa üstü mesaidir (51 × 4 = aylık 204)
--   O-009  Günlük mevcut dengesi   fazla kadro günlere eşit dağılsın (yumuşak)
--   C-003  Haftalık 50 sa referansı KALDIRILDI — yerini C-026 ve O-001 aldı.
--
-- "Yasal" kurallar esnek yapılamaz ama SAYILARI düzenlenebilir (Baran, 30.09):
-- başka bir kurum başka bir yasal süreyle çalışabilir.
--
-- Tekrar çalıştırılabilir: ON CONFLICT / koşullu UPDATE.

BEGIN;

-- ---------------------------------------------------------------------------
-- 1) Yeni kurallar
-- ---------------------------------------------------------------------------
INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source) VALUES
    ('weekly_legal_min_net_hours',
     'Haftalık yasal asgari çalışma',
     'Her Pzt–Paz haftasında mola düşülmüş NET çalışma en az 45 saattir. Yıllık izin '
     've rapor günü 7,5 saat sayılır. Ay başındaki yarım hafta yayınlanmış önceki '
     'çizelgeyle tamamlanır; ay sonundaki yarım haftada süre gün sayısıyla orantılıdır.',
     TRUE, NULL, 'hafta', 'yasal'),
    ('monthly_legal_min_net_hours',
     'Aylık yasal asgari çalışma',
     'Takvim ayında mola düşülmüş NET çalışma en az 180 saattir. Yıllık izin ve rapor '
     'günü 7,5 saat sayılır. Aylık 200 saat hedefi (C-004) ayrı bir kuraldır.',
     TRUE, NULL, 'ay', 'yasal'),
    ('weekly_work_days',
     'Haftalık çalışma günü',
     'Her Pzt–Paz haftasında en az 5 gün çalışılır, en fazla 2 gün izin yapılır. '
     'Yıllık izin, rapor ve kesin izin istekleri bu sayıma girmez. 2 gün üst üste '
     'izin serbesttir; sınır haftadaki TOPLAM izin günüdür.',
     TRUE, NULL, 'hafta', 'kurumsal'),
    ('daily_crew_balance',
     'Günlük mevcut dengesi',
     'Asgari kadronun üstündeki fazla kişi günlere eşit dağılır: bir gün 5, ertesi '
     'gün 8 kişi yerine her gün 6–7. Yumuşak: kapsamanın ve saat kurallarının önüne geçmez.',
     FALSE, 2000, 'gun', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

UPDATE constraints SET catalog_code = 'C-026' WHERE code = 'weekly_legal_min_net_hours'  AND catalog_code IS NULL;
UPDATE constraints SET catalog_code = 'C-027' WHERE code = 'monthly_legal_min_net_hours' AND catalog_code IS NULL;
UPDATE constraints SET catalog_code = 'C-028' WHERE code = 'weekly_work_days'            AND catalog_code IS NULL;
UPDATE constraints SET catalog_code = 'O-009' WHERE code = 'daily_crew_balance'          AND catalog_code IS NULL;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, x.anahtar, x.deger, x.aciklama
FROM (VALUES
    ('weekly_legal_min_net_hours',  'weekly_min_net_hours',       45,
     'Haftalık asgari NET saat (mola hariç)'),
    ('weekly_legal_min_net_hours',  'absence_daily_credit_hours', 7.5,
     'İzin/rapor günü haftalık asgariye kaç saat sayılır'),
    ('monthly_legal_min_net_hours', 'monthly_legal_min_net_hours', 180,
     'Aylık asgari NET saat (mola hariç)'),
    ('weekly_work_days',            'min_weekly_work_days',        5,
     'Haftada en az çalışılan gün'),
    ('weekly_work_days',            'max_weekly_off_days',         2,
     'Haftada en fazla izin (boş) gün'),
    ('overtime_minimization',       'weekly_paid_gross_hours',    51,
     'Haftalık ücret bazı, BRÜT saat. Üstü fazla mesaidir.'),
    ('overtime_minimization',       'monthly_paid_gross_hours',  204,
     'Aylık ücret bazı, BRÜT saat (bilgi: 51 × 4)')
) AS x (kural, anahtar, deger, aciklama)
JOIN constraints c ON c.code = x.kural
ON CONFLICT (constraint_id, param_key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 2) Değişen kurallar
-- ---------------------------------------------------------------------------
-- C-025 karma hafta artık zorunlu (Baran, 30.09): "full geceler, full gündüzler
-- çıkmasın". Zorunlu kuralın ağırlığı olmaz (ck_constraints_weight_by_type).
UPDATE constraints
   SET is_hard = TRUE, default_weight = NULL,
       description = 'Gündüz ve gece çalışabilen personelin her haftasında en az 1 gündüz '
                     've en az 1 gece bulunur. İzinli/raporlu günü olan hafta muaftır; '
                     'oryantasyondakiler eşlerini izlediği için muaftır.'
 WHERE code = 'mixed_shift_week' AND is_hard IS DISTINCT FROM TRUE;

-- O-001'in anlamı değişti: eskiden aylık 200 saat üstü NET, artık haftalık 51 saat
-- üstü BRÜT (hastanenin maaş hesabı böyle).
UPDATE constraints
   SET name = 'Fazla mesai',
       description = 'Haftalık BRÜT (molalar dahil) 51 saatin üstündeki her saat fazla '
                     'mesaidir; aylık mesai haftalık fazlaların toplamıdır. Yarım hafta, '
                     'Pazar gününün düştüğü aya yazılır. Yumuşak: solver mesaiyi azaltmaya çalışır.'
 WHERE code = 'overtime_minimization';

-- ---------------------------------------------------------------------------
-- 3) C-003 (haftalık 50 sa referansı) kaldırılıyor
-- ---------------------------------------------------------------------------
-- Satırı olan kural açıktır; kapatmanın yolu satırı silmek (constraints'te
-- aktif/pasif kolonu yok). Parametresi CASCADE ile, teşhis bağlantıları
-- SET NULL ile düşer (migration 001, 007).
DELETE FROM constraints WHERE code = 'weekly_reference_hours';

COMMIT;
