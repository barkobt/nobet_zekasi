-- seeds/015_fairness_weights.sql
-- 28.09.2026: Adalet kuralları (O-003, O-004, O-005) ve yumuşak ağırlıkların
-- ETKİN değerlere çekilmesi.
--
-- NEDEN AĞIRLIKLAR DEĞİŞİYOR: Notion'dan gelen 200/220 değerleri istenen önceliği
-- ifade etmiyordu — O-001 (fazla mesai) 200 ile O-002 (adalet) 220 neredeyse eşitti,
-- oysa adalet fazla mesainin açıkça önünde olmalı. Ağırlık sıralaması KODA gizli
-- çarpan olarak konmuyor; veritabanında duruyor ki E-03'te görünsün ve hastane
-- değiştirince etkisi tahmin edilebilir olsun.
--
-- KADEMELER (gerçekçi toplam katkılarıyla):
--   1. Kapsama/görev eksiği   — katı, kodda 100.000.000/kişi
--   2. C-004 eksik saat       — katı, kodda 50.000/yarım saat
--   3. Adalet O-002/003/004   — 2.200            → toplam ≈ 12.000.000
--   4. O-001 fazla mesai, O-005 ambulans dengesi — 200  → toplam ≈ 400.000
--   5. C-003 haftalık 50 saat — 10               → toplam ≈ 30.000
--
-- BİRİM ÖLÇEĞİ koda ait ve oradadır (solver/model.py): ağırlık "yarım saat"
-- başınadır; gece/hafta sonu sayıları vardiya süresiyle çarpılarak yarım saate
-- çevrilir. Veritabanındaki sayı saf ÖNCELİKTİR, birim dönüşümü değil.
--
-- Tekrar çalıştırılabilir: INSERT'ler ON CONFLICT, UPDATE'ler koşulsuz.

BEGIN;

-- Kademe 3: adalet
UPDATE constraints SET default_weight = 2200
WHERE code = 'fairness_balance' AND default_weight IS DISTINCT FROM 2200;

INSERT INTO constraints (code, name, description, is_hard, default_weight, scope, source, catalog_code)
VALUES
  ('night_fairness', 'Gece adaleti',
   'Gece çalışabilen personel arasında gece sayıları dengeli dağıtılır. Hem en çok ile '
   'en az arasındaki fark hem de kişilerin ortalamaya uzaklığı cezalandırılır. '
   'Sadece gündüz çalışanlar hesaba girmez: onların gece sayısı zorunlu olarak sıfırdır.',
   FALSE, 2200, 'ay', 'kurumsal', 'O-003'),

  ('weekend_fairness', 'Hafta sonu adaleti',
   'Cumartesi ve Pazar vardiyaları personel arasında dengeli dağıtılır.',
   FALSE, 2200, 'ay', 'kurumsal', 'O-004'),

  -- Kademe 4: ambulans bir GÖREV, vardiya kadar yük değil → fazla mesai seviyesinde
  ('ambulance_fairness', 'Ambulans görev dengesi',
   'Ambulans görevi, yetkinliği olan personel arasında dengeli dağıtılır. '
   'Yetkinliği olmayanlar hesaba girmez.',
   FALSE, 200, 'ay', 'kurumsal', 'O-005')
ON CONFLICT (code) DO NOTHING;

COMMIT;
