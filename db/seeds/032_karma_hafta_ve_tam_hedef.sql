-- 032_karma_hafta_ve_tam_hedef.sql
-- Baran, 29.09.2026 — iki denge düzeltmesi.
--
-- 1) KARMA HAFTA (C-025)
--    Solver bazı haftalarda gündüz+gece çalışabilen birine haftanın tamamını
--    gece (ya da tamamını gündüz) yazıyordu. Gece 11 saat olduğu için tam gece
--    haftası 3-4 vardiyada doluyor ve geriye 3-4 boş gün kalıyor; aynı hafta
--    başka birine tamamen gündüz düşüyor. Ölçüm (Ekim 2026, 60 kişi-hafta):
--    4 yalnız-gece, 17 yalnız-gündüz, 39 karma.
--
--    Kural: gündüz+gece çalışabilen personelin her tam haftasında EN AZ 1 gündüz
--    ve EN AZ 1 gece bulunsun. YUMUŞAK — gerçekten gerekiyorsa tek tip hafta
--    kurulabilir, ama bedeli var. Sadece-gündüz ve sadece-gece personele
--    uygulanmaz (onlar zaten tek tip).
--
-- 2) HEDEFE TAM ULAŞMA (C-004 parametresi)
--    Vardiyalar 490 ve 660 dakikalık parçalar; 10 gece + 11 gündüz = 11.990 dk
--    = 199,83 saat çıkıyor ve 200'ün 10 dakika altında kalıyor. Bir vardiya daha
--    eklemek 208 saate fırlatıyor, solver da 10 dakikalık açığı tercih ediyordu.
--    Artık hedefi TAM dolduran her kişi ayrıca ödüllendiriliyor: hedefin altında
--    kalmak, açığın büyüklüğünden bağımsız sabit bir ceza daha yazar.

BEGIN;

INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source) VALUES
    ('mixed_shift_week',
     'Karma hafta',
     'Gündüz ve gece çalışabilen personelin her tam haftasında en az 1 gündüz ve '
     'en az 1 gece bulunur. Tek tip hafta gece 11 saat olduğu için az vardiyada '
     'dolar ve 3-4 boş gün bırakır; aynı hafta başka birine tamamen gündüz düşer. '
     'Yumuşak: gerekirse tek tip hafta kurulabilir.',
     FALSE, 800, 'hafta', 'kurumsal')
ON CONFLICT (code) DO NOTHING;

UPDATE constraints SET catalog_code = 'C-025'
 WHERE code = 'mixed_shift_week' AND catalog_code IS NULL;

INSERT INTO constraint_params (constraint_id, param_key, param_value, description)
SELECT c.id, 'exact_target_penalty', 40000,
       'Aylık hedefi TAM dolduramayan kişi başına ek ceza; açığın büyüklüğünden '
       'bağımsız sabit. 10 dakikalık açığı kapatmayı kârlı kılar. Ölçüm: 5.000 '
       'yetmiyor, 40.000 yetiyor.'
FROM constraints c WHERE c.code = 'monthly_min_hours'
ON CONFLICT (constraint_id, param_key)
DO UPDATE SET param_value = EXCLUDED.param_value, description = EXCLUDED.description;

COMMIT;
