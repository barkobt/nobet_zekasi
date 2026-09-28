-- 014_request_status.up.sql
-- 27.09.2026: Personel isteği (Orquest'teki "Requests") modeli.
--
-- SORUN: availability_rules türü tutuyordu ama DURUMU tutamıyordu. Onay bilgisi
-- hiçbir yerde durmadığı için solver "kesin kural" ile "cezalı tercih"i ayırt
-- edemiyordu.
--   ONAYLANDI → solver için kesin kısıt (o gün/vardiya dışı yazılamaz)
--   BEKLEMEDE → cezalı tercih; karşılanamazsa teşhiste görünür
-- İstek, izinden farklı olarak aylık hedef saati DÜŞÜRMEZ (yalnız absences düşürür).
--
-- Yeni tür sözlüğü: BOS_GUN (o gün çalışmasın) · SADECE_GUNDUZ · SADECE_GECE.
--
-- NEDEN ESKİ DEĞERLER SİLİNMİYOR: 'off_talebi' / 'acilis_tercihi' / 'kapanis_tercihi'
-- bugün E-02'de canlı — api/app/schemas/people.py'deki RuleType Literal'ı ve
-- web/src/lib/personel.ts'teki açılır liste bu değerleri POST ediyor. CHECK'i
-- daraltmak çalışan bir ekranı bozar. Bu migration EKLEYİCİDİR; eski değerlerin
-- kaldırılması İstekler sekmesi yazıldığında ayrı bir migration olacak.
--
-- ÇELİŞKİ NOTU: uq_availability_rules_staff_date_type hâlâ (staff_id, target_date,
-- rule_type) üzerinde. Yani aynı güne hem BOS_GUN hem SADECE_GECE yazılabilir; bu
-- çelişki bilinçli olarak şimdilik açık bırakıldı (İstekler sekmesiyle çözülecek).

ALTER TABLE availability_rules
    ADD COLUMN status TEXT NOT NULL DEFAULT 'BEKLEMEDE';

ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_status
    CHECK (status IN ('BEKLEMEDE', 'ONAYLANDI'));

ALTER TABLE availability_rules DROP CONSTRAINT ck_availability_rules_type;

ALTER TABLE availability_rules
    ADD CONSTRAINT ck_availability_rules_type
    CHECK (rule_type IN (
        -- yeni sözlük
        'BOS_GUN', 'SADECE_GUNDUZ', 'SADECE_GECE',
        -- eski sözlük: E-02 hâlâ bunları gönderiyor, geçiş bitince düşecek
        'off_talebi', 'acilis_tercihi', 'kapanis_tercihi'
    ));

COMMENT ON COLUMN availability_rules.status IS
    'BEKLEMEDE: solver için cezalı tercih · ONAYLANDI: solver için kesin kural';

COMMENT ON COLUMN availability_rules.rule_type IS
    'BOS_GUN: o gün çalışmasın · SADECE_GUNDUZ · SADECE_GECE. '
    'off_talebi/acilis_tercihi/kapanis_tercihi eski sözlüktür, E-02 geçişi bitince düşecek.';
