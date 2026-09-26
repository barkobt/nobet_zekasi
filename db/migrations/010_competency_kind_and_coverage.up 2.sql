-- 010_competency_kind_and_coverage.up.sql
-- Yetkinlik modelinin netleştirilmesi (25.09.2026 kararı) + kapsama görünümünün düzeltilmesi.
--
-- SORUN: v_daily_coverage her slotu assignment_tasks (görev rozeti) üzerinden sayıyordu.
-- Ama TRIYAJ/AMBULANS/GOZLEM bir GÖREVdir (o vardiyada o işi yapıyor), SAYIM/SHIFT_YETKILISI
-- ise KİŞİNİN YETKİNLİĞİdir (o vardiyada böyle biri var mı?). İkisi aynı yerden sayılamaz:
-- referans haftada SAYIM ve SHIFT_YETKILISI her gün 0 çıkıyordu.
-- queries/reference_week_audit.sql bu ayrımı zaten elle yapıyordu; artık şema yapıyor.

---------------------------------------------------------------------------
-- A) YAPI
---------------------------------------------------------------------------

-- A1) Yetkinliğin türü. Değerleri VERİdir → seeds/010'da atanır.
--     DEFAULT 'QUALIFICATION': ileride eklenen yetkinlik, aksi söylenmedikçe görev değildir.
ALTER TABLE competencies
    ADD COLUMN kind TEXT NOT NULL DEFAULT 'QUALIFICATION';

ALTER TABLE competencies
    ADD CONSTRAINT ck_competencies_kind CHECK (kind IN ('TASK', 'QUALIFICATION'));

COMMENT ON COLUMN competencies.kind IS
    'TASK: vardiya içinde atanan görev, assignment_tasks''tan sayılır (TRIYAJ, AMBULANS, GOZLEM). '
    'QUALIFICATION: kişinin taşıdığı yetki, staff_competencies''ten sayılır (SAYIM, SHIFT_YETKILISI, ...).';

-- A2) Katalog kodu: docs/kisit-katalogu.md''deki C-001…O-002 kodları.
--     Hastane bu dille konuşuyor ("C-011 ile C-016 çatışıyor"); E-03 ve E-10 bunu gösterecek.
--     NULL olabilir: kataloğa sonradan eklenmemiş kurallar var (count_authority_required).
ALTER TABLE constraints
    ADD COLUMN catalog_code TEXT;

ALTER TABLE constraints
    ADD CONSTRAINT uq_constraints_catalog_code UNIQUE (catalog_code);

-- A3) İhtiyaç satırı ↔ kural bağı.
--     İş bölümü: satır "ne, kaç kişi" der (E-06); kural "zorunlu mu, cezası ne,
--     gevşetilebilir mi" der (E-03). Hard/soft bilgisi constraints''te TEK yerde durur;
--     need_template_rows''a ikinci bir bayrak konmaz, yoksa E-03''te gevşetilen kural
--     şablonda katı kalırdı.
--     NULL = bağlanmamış satır, "hard, ağırlıksız" varsayılır.
ALTER TABLE need_template_rows
    ADD COLUMN constraint_id BIGINT;

ALTER TABLE need_template_rows
    ADD CONSTRAINT fk_ntr_constraint
        FOREIGN KEY (constraint_id) REFERENCES constraints(id) ON DELETE SET NULL;

---------------------------------------------------------------------------
-- B) KAPSAMA GÖRÜNÜMÜ — kind''a göre sayım
---------------------------------------------------------------------------
-- Sayım kuralı SATIR bazında değil YETKİNLİK bazındadır: bir ihtiyaç satırının istediği
-- her yetkinlik kendi kind''ına göre değerlendirilir, sonuçlar VE''lenir.
-- Buna mecburuz çünkü TRIYAJ satırı karışık: TRIYAJ (TASK) + HASTA_ILT (QUALIFICATION).
--
-- 009''dan farklar: (1) kind''a göre sayım, (2) ast.unit_id = nst.unit_id filtresi.
-- Birim filtresi bugün zararsız (tek birim) ama 24h vardiya bir gün açılırsa
-- aynı atamanın hem gündüze hem geceye sayılmasını engeller.

CREATE OR REPLACE VIEW v_daily_coverage AS
WITH days AS (
    SELECT d.id AS draft_id, d.unit_id, gs::date AS day
    FROM schedule_drafts d,
         generate_series(d.month_start,
                         (d.month_start + INTERVAL '1 month' - INTERVAL '1 day')::date,
                         INTERVAL '1 day') AS gs
)
SELECT
    days.draft_id,
    days.day,
    nst.code       AS shift_code,
    ntr.slot_code,
    ntr.min_count  AS required,
    (
        SELECT COUNT(*)
        FROM assignments a
        JOIN shift_types ast ON ast.id = a.shift_type_id
        JOIN staff s         ON s.id  = a.staff_id
        JOIN roles ro        ON ro.id = s.role_id
        WHERE a.draft_id  = days.draft_id
          AND a.work_date = days.day
          AND ast.unit_id = nst.unit_id
          AND ast.start_time = nst.start_time
          AND CASE
                -- Yetkinlik şartı yok → GENEL mevcut.
                -- 24.09 kararı korunuyor: sorumlu ve oryantasyondakiler sayılmaz.
                WHEN NOT EXISTS (SELECT 1 FROM need_template_row_competencies x
                                 WHERE x.need_template_row_id = ntr.id)
                THEN (NOT s.is_orientation AND ro.code <> 'sorumlu_hemsire')

                -- Şart varsa: istenen HER yetkinlik kendi kind'ına göre sağlanmalı.
                -- "Sağlanmayan tek bir yetkinlik bile yok" = NOT EXISTS (...)
                ELSE NOT EXISTS (
                    SELECT 1
                    FROM need_template_row_competencies x
                    JOIN competencies c ON c.id = x.competency_id
                    WHERE x.need_template_row_id = ntr.id
                      AND NOT (
                          (c.kind = 'TASK' AND EXISTS (
                              SELECT 1 FROM assignment_tasks t
                              WHERE t.assignment_id = a.id AND t.competency_id = c.id))
                          OR
                          (c.kind = 'QUALIFICATION' AND EXISTS (
                              SELECT 1 FROM staff_competencies sc
                              WHERE sc.staff_id = a.staff_id AND sc.competency_id = c.id))
                      )
                )
              END
    )              AS assigned
FROM days
JOIN need_periods np        ON np.unit_id = days.unit_id AND np.valid_period @> days.day
JOIN need_template_rows ntr ON ntr.need_template_id = np.need_template_id
JOIN shift_types nst        ON nst.id = ntr.shift_type_id;

---------------------------------------------------------------------------
-- C) UYGUNLUK KONTROLÜ — trigger (yazma anı) + denetim view'ı (geçmiş)
---------------------------------------------------------------------------
-- NEDEN BİLEŞİK FK DEĞİL: assignment_tasks'a staff_id denormalize edip
-- (staff_id, competency_id) → staff_competencies FK'si kurmak tamamen bildirimsel olurdu,
-- AMA E-02'de bir yetkinliği geri almak (DELETE FROM staff_competencies) geçmiş ataması
-- olan kişide FK'ye takılırdı. Bugünkü bir değişiklik geçmişi yeniden yazamaz.
--
-- KAPSAM: trigger PLANI korur, GEÇMİŞİ yeniden yazmaz.
--   source = 'solver'                → hata fırlatır (üretilen plan baştan doğru olmalı)
--   source = 'manuel' / 'onceki_ay'  → uyarı verir, engellemez
-- Bunun iki sebebi var:
--   1) seeds/009 kağıt çizelgenin birebir aktarımıdır (source='manuel') ve içinde gerçek
--      bir ihlal var (Güven Göl, 26.09, AMBULANS — oryantasyonda, yetkinlik kaydı yok).
--      Kağıttaki gerçeği kurala uydurmak için seed'i değiştirmiyoruz.
--   2) docs/ekran-haritasi.md E-09: "manuel müdahale ... hangi kuralın ihlal edildiğini
--      anında söyler, ENGELLEMEZ." Trigger bu kararla aynı hizada.
-- Hiçbir durumda kaçan yok: v_task_eligibility_violations her ikisini de listeler.

CREATE FUNCTION trg_assignment_tasks_check_eligibility() RETURNS trigger AS $$
DECLARE
    v_comp   RECORD;
    v_source TEXT;
    v_staff  RECORD;
BEGIN
    SELECT code, name, kind INTO v_comp FROM competencies WHERE id = NEW.competency_id;

    IF v_comp.kind <> 'TASK' THEN
        RAISE EXCEPTION
            'Yetkinlik "%" görev olarak atanamaz (kind=%). Görev olabilecekler: kind = TASK.',
            v_comp.code, v_comp.kind
            USING ERRCODE = 'check_violation';
    END IF;

    SELECT a.source, s.full_name INTO v_source, v_staff
    FROM assignments a JOIN staff s ON s.id = a.staff_id
    WHERE a.id = NEW.assignment_id;

    IF NOT EXISTS (SELECT 1 FROM staff_competencies sc
                   WHERE sc.staff_id = (SELECT staff_id FROM assignments WHERE id = NEW.assignment_id)
                     AND sc.competency_id = NEW.competency_id) THEN
        IF v_source = 'solver' THEN
            RAISE EXCEPTION
                '% kişisinde "%" yetkinliği yok, bu görev atanamaz.', v_staff.full_name, v_comp.code
                USING ERRCODE = 'check_violation';
        ELSE
            RAISE WARNING
                '% kişisinde "%" yetkinliği yok (kaynak: %). Kayıt alındı, v_task_eligibility_violations''ta listelenecek.',
                v_staff.full_name, v_comp.code, v_source;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER assignment_tasks_check_eligibility
    BEFORE INSERT OR UPDATE ON assignment_tasks
    FOR EACH ROW EXECUTE FUNCTION trg_assignment_tasks_check_eligibility();

-- Denetim view'ı: trigger'ın göremediği iki deliği de kapatır —
--   (1) trigger'dan ÖNCE yazılmış satırlar, (2) yetkinliğin SONRADAN geri alınması.
CREATE VIEW v_task_eligibility_violations AS
SELECT
    a.draft_id,
    a.id          AS assignment_id,
    a.staff_id,
    s.full_name,
    a.work_date,
    st.code       AS shift_code,
    c.code        AS task_code,
    c.name        AS task_name,
    a.source
FROM assignment_tasks t
JOIN assignments a   ON a.id  = t.assignment_id
JOIN staff s         ON s.id  = a.staff_id
JOIN shift_types st  ON st.id = a.shift_type_id
JOIN competencies c  ON c.id  = t.competency_id
WHERE NOT EXISTS (
    SELECT 1 FROM staff_competencies sc
    WHERE sc.staff_id = a.staff_id AND sc.competency_id = t.competency_id
);
