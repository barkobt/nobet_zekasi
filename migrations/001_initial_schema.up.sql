CREATE TABLE units (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code       VARCHAR(50)  NOT NULL,
    name       VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_units_code UNIQUE (code)
);

CREATE TABLE shift_types (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id          BIGINT       NOT NULL,
    code             VARCHAR(50)  NOT NULL,
    name             VARCHAR(100) NOT NULL,
    start_time       TIME         NOT NULL,
    duration_hours   NUMERIC(4,2) NOT NULL,
    crosses_midnight BOOLEAN GENERATED ALWAYS AS
        ((EXTRACT(EPOCH FROM start_time) / 3600 + duration_hours) > 24) STORED,
    created_at       TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_shift_types_unit FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE CASCADE,
    CONSTRAINT uq_shift_types_unit_code UNIQUE (unit_id, code)
);

CREATE TABLE competencies (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code        VARCHAR(50)  NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_competencies_code UNIQUE (code)
);

CREATE TABLE constraints (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code           VARCHAR(50)  NOT NULL,
    name           VARCHAR(100) NOT NULL,
    description    TEXT,
    is_hard        BOOLEAN      NOT NULL DEFAULT TRUE,
    default_weight INTEGER      NOT NULL DEFAULT 100,
    created_at     TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_constraint_code UNIQUE (code)
);

CREATE TABLE constraint_params (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    constraint_id BIGINT        NOT NULL,
    param_key     VARCHAR(50)   NOT NULL,
    param_value   NUMERIC(10,2) NOT NULL,
    description   VARCHAR(200),
    updated_at    TIMESTAMPTZ   DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_constraint_params_constraint FOREIGN KEY (constraint_id) REFERENCES constraints(id) ON DELETE CASCADE,
    CONSTRAINT uq_constraint_params_key UNIQUE (constraint_id, param_key)
);

