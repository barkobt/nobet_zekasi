-- seeds/018_hastane_kararlari.sql
-- 28.09.2026: Hastane teyidinden gelen kural kararları.
--
-- 1) İZİN DÜŞÜMÜ KESİNLEŞTİ
--    7,5 saat "geçici" değil; hastane onayladı.
UPDATE constraint_params
SET description = 'İzin/rapor günü başına aylık hedeften düşülen saat. Hastane onayladı (28.09.2026).'
WHERE param_key = 'absence_daily_reduction_hours';

-- 2) EKSİK CEZALARI EŞİTLENDİ
--    Hastane: "hepsi eşit derecede kabul edilemez." Kademeli ağırlıklar
--    (2.000.000 … 500.000) kaldırıldı; hepsi en yüksek değere çekildi.
--    200 saat eksiğinin cezasından (kodda 20.000/yarım saat) büyük kalıyor:
--    bir slot eksiği = 100 yarım saat = 50 saatlik hedef eksiğine bedel.
UPDATE constraints
SET default_weight = 2000000
WHERE code IN ('day_shift_min_crew', 'night_shift_min_crew', 'shift_lead_required',
               'triage_pool_min_size', 'ambulance_crew_size', 'observation_pool_separate',
               'all_crew_triage_or_observation', 'count_authority_required')
  AND default_weight IS DISTINCT FROM 2000000;

UPDATE constraints
SET description = regexp_replace(description, '\s*\[Eksik cezası hastane teyidi beklemektedir\.\]', '')
                  || ' [Eksik cezaları hastane kararıyla eşitlendi (28.09.2026).]'
WHERE code IN ('day_shift_min_crew', 'night_shift_min_crew', 'shift_lead_required',
               'triage_pool_min_size', 'ambulance_crew_size', 'observation_pool_separate',
               'all_crew_triage_or_observation', 'count_authority_required')
  AND description NOT LIKE '%eşitlendi%';

-- 3) AMBULANS ALAN DAĞILIMI TERCİHİ ZAYIFLADI
--    Hastane: "2 triyajdan olur, 1+1 olur, 2 gözlemden olmaz."
--    "2 gözlemden olmaz" zaten C-009'un katı sonucudur (gözlemde 2 kişi var,
--    ikisi de çıkarsa alan boşalır). Geriye kalan 1+1 yalnız bir TERCİH, o yüzden
--    ağırlığı adalet kademesinden (2.200) fazla mesai kademesine (200) indi.
UPDATE constraints
SET default_weight = 200,
    description = 'Ambulansa çıkan 2 kişi mümkünse 1 triyajdan + 1 gözlemden olur. '
                  '2 kişinin de triyajdan çıkması SERBESTTİR (küçük ceza); 2 kişinin de '
                  'gözlemden çıkması C-009 ile zaten imkânsızdır. Hastane kararı (28.09.2026).'
WHERE code = 'ambulance_area_split';
