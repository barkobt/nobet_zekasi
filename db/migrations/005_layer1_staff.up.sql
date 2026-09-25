-- 005_layer1_staff.up.sql
-- Katman 1: kadro tabloları

CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TABLE roles (
    id   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(50)  NOT NULL,
    name VARCHAR(100) NOT NULL,
    CONSTRAINT uq_roles_code UNIQUE (code)
);

CREATE TABLE staff (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sicil_no           VARCHAR(50),
    role_id            BIGINT       NOT NULL,
    full_name          VARCHAR(150) NOT NULL,
    shift_eligibility  TEXT         NOT NULL,
    seniority_years    NUMERIC(4,1),
    is_orientation     BOOLEAN      NOT NULL DEFAULT FALSE,
    buddy_staff_id     BIGINT,
    note               TEXT,
    created_at         TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_staff_role  FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT,
    CONSTRAINT fk_staff_buddy FOREIGN KEY (buddy_staff_id) REFERENCES staff(id) ON DELETE SET NULL,
    CONSTRAINT uq_staff_sicil_no UNIQUE (sicil_no),
    CONSTRAINT ck_staff_eligibility
        CHECK (shift_eligibility IN ('gunduz_gece', 'sadece_gunduz', 'sadece_gece')),
    CONSTRAINT ck_staff_orientation_buddy
        CHECK (NOT is_orientation OR buddy_staff_id IS NOT NULL),
    CONSTRAINT ck_staff_not_own_buddy
        CHECK (buddy_staff_id IS NULL OR buddy_staff_id <> id)
);

CREATE TABLE contracts (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_id              BIGINT    NOT NULL,
    valid_period          DATERANGE NOT NULL,
    monthly_target_hours  NUMERIC(6,2),
    note                  TEXT,
    created_at            TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contracts_staff FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT ex_contracts_no_overlap
        EXCLUDE USING gist (staff_id WITH =, valid_period WITH &&)
);

CREATE TABLE staff_competencies (
    staff_id       BIGINT NOT NULL,
    competency_id  BIGINT NOT NULL,
    PRIMARY KEY (staff_id, competency_id),
    CONSTRAINT fk_staff_competencies_staff      FOREIGN KEY (staff_id)      REFERENCES staff(id)        ON DELETE CASCADE,
    CONSTRAINT fk_staff_competencies_competency FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE CASCADE
);

CREATE TABLE availability_rules (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_id     BIGINT NOT NULL,
    target_date  DATE   NOT NULL,
    rule_type    TEXT   NOT NULL,
    note         TEXT,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_availability_rules_staff FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT ck_availability_rules_type
        CHECK (rule_type IN ('off_talebi', 'acilis_tercihi', 'kapanis_tercihi')),
    CONSTRAINT uq_availability_rules_staff_date_type UNIQUE (staff_id, target_date, rule_type)
);

CREATE TABLE absences (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    staff_id      BIGINT    NOT NULL,
    period        DATERANGE NOT NULL,
    absence_type  TEXT      NOT NULL,
    note          TEXT,
    created_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_absences_staff FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT ck_absences_type
        CHECK (absence_type IN ('yillik_izin', 'rapor', 'ucretsiz_izin', 'diger')),
    CONSTRAINT ex_absences_no_overlap
        EXCLUDE USING gist (staff_id WITH =, period WITH &&)
);

CREATE TABLE staff_conflicts (
    staff_id_low   BIGINT NOT NULL,
    staff_id_high  BIGINT NOT NULL,
    note           TEXT,
    created_at     TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (staff_id_low, staff_id_high),
    CONSTRAINT fk_staff_conflicts_low  FOREIGN KEY (staff_id_low)  REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT fk_staff_conflicts_high FOREIGN KEY (staff_id_high) REFERENCES staff(id) ON DELETE CASCADE,
    CONSTRAINT ck_staff_conflicts_order CHECK (staff_id_low < staff_id_high)
);
