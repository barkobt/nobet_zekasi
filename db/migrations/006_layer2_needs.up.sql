-- 006_layer2_needs.up.sql
-- Katman 2: "Hangi gün, hangi vardiyada, kaç kişi, hangi yetkinlikle gerekiyor?"
--
-- FK REFLEKSİ (her tabloda aynı soruyu sor):
--   "Bir X'in kaç tane Y'si olabilir?"  →  "çok" olan taraf FK'yi taşır.
--   Bir şablonun ÇOK satırı var          → need_template_rows.need_template_id
--   Bir vardiya tipi ÇOK satırda geçer   → need_template_rows.shift_type_id
--   Bir satır ÇOK yetkinlik isteyebilir,
--   bir yetkinlik ÇOK satırda geçebilir  → iki taraf da çok = köprü tablo

-- 1) Şablon başlığı: "Standart Hafta", "Bayram Haftası"
CREATE TABLE need_templates (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       VARCHAR(50)  NOT NULL,
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_need_templates_code UNIQUE (code)
);

-- 2) Şablonun satırları: "Standart şablonda, GECE vardiyasında, TRIYAJ slotunda en az 3 kişi"
--    slot_code: satırı insan diliyle tanımlayan kısa kod (GENEL, SHIFT_YETKILISI, TRIYAJ, AMBULANS, GOZLEM).
--    Neden var? Seed'de ve solver'da satırı "note" metniyle değil, sabit bir kodla bulmak için.
--    UNIQUE (şablon, vardiya, slot): aynı şablonda aynı vardiyaya aynı slot iki kez girilemez.
CREATE TABLE need_template_rows (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    need_template_id BIGINT      NOT NULL,
    shift_type_id    BIGINT      NOT NULL,
    slot_code        VARCHAR(30) NOT NULL,
    min_count        INTEGER     NOT NULL,
    note             TEXT,
    CONSTRAINT fk_ntr_template FOREIGN KEY (need_template_id) REFERENCES need_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_ntr_shift    FOREIGN KEY (shift_type_id)    REFERENCES shift_types(id)    ON DELETE RESTRICT,
    CONSTRAINT uq_ntr_template_shift_slot UNIQUE (need_template_id, shift_type_id, slot_code),
    CONSTRAINT ck_ntr_min_count CHECK (min_count > 0)
);
-- ON DELETE seçimleri:
--   Şablon silinirse satırları anlamsızdır  → CASCADE (birlikte silinsin)
--   Vardiya tipi silinmeye çalışılırsa     → RESTRICT (şablonlar ona bağlıyken silinemesin;
--                                              vardiyayı kapatmak için is_active = FALSE kullan)

-- 3) Köprü: bir satırın istediği yetkinlikler (birden fazlaysa HEPSİ gerekir = VE mantığı)
--    Satırın burada kaydı yoksa: "yetkinlik şartı yok, genel mevcut" demektir.
CREATE TABLE need_template_row_competencies (
    need_template_row_id BIGINT NOT NULL,
    competency_id        BIGINT NOT NULL,
    PRIMARY KEY (need_template_row_id, competency_id),
    CONSTRAINT fk_ntrc_row        FOREIGN KEY (need_template_row_id) REFERENCES need_template_rows(id) ON DELETE CASCADE,
    CONSTRAINT fk_ntrc_competency FOREIGN KEY (competency_id)        REFERENCES competencies(id)       ON DELETE RESTRICT
);

-- 4) Hangi tarihte hangi şablon geçerli (Orquest'teki "Needs periods")
--    EXCLUDE: aynı birimde çakışan iki tarih aralığına iki şablon bağlanamaz.
CREATE TABLE need_periods (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id          BIGINT    NOT NULL,
    need_template_id BIGINT    NOT NULL,
    valid_period     DATERANGE NOT NULL,
    CONSTRAINT fk_np_unit     FOREIGN KEY (unit_id)          REFERENCES units(id)          ON DELETE CASCADE,
    CONSTRAINT fk_np_template FOREIGN KEY (need_template_id) REFERENCES need_templates(id) ON DELETE RESTRICT,
    CONSTRAINT ex_np_no_overlap
        EXCLUDE USING gist (unit_id WITH =, valid_period WITH &&)
);
