-- 007_layer3_solution.up.sql
-- Katman 3: Solver'ın ürettiği çizelge ve çalışma kayıtları
--
-- Zincir (her ok "çok tarafı FK taşır" kuralıyla):
--   schedule_drafts (1) ──< solver_runs (N) ──< solver_diagnostics (N)
--   schedule_drafts (1) ──< assignments (N) ──< assignment_tasks (N) >── competencies
--                                    assignments (1) ── actual_times (0..1)

-- 1) Taslak: "Ekim 2026 için 2. deneme çizelgesi"
--    month_start: ayın ilk günü (2026-10-01). CHECK ile başka bir gün girilemez.
--    status: taslak → yayinlandi → arsiv
CREATE TABLE schedule_drafts (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    unit_id      BIGINT       NOT NULL,
    month_start  DATE         NOT NULL,
    name         VARCHAR(100) NOT NULL,
    status       TEXT         NOT NULL DEFAULT 'taslak',
    created_at   TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,
    CONSTRAINT fk_drafts_unit FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE RESTRICT,
    CONSTRAINT ck_drafts_status CHECK (status IN ('taslak', 'yayinlandi', 'arsiv')),
    CONSTRAINT ck_drafts_month_start CHECK (EXTRACT(DAY FROM month_start) = 1),
    CONSTRAINT ck_drafts_published_at CHECK (status <> 'yayinlandi' OR published_at IS NOT NULL)
);

-- Aynı birim + aynı ay için en fazla BİR yayınlanmış taslak.
-- "Partial" = sadece WHERE koşulunu sağlayan satırlar için benzersizlik aranır.
-- Taslak ve arşiv satırları istediği kadar olabilir, yayınlanmış olan tek olmalı.
CREATE UNIQUE INDEX uq_drafts_one_published
    ON schedule_drafts (unit_id, month_start)
    WHERE status = 'yayinlandi';

-- 2) Solver koşusu: her "Çöz" tıklaması bir satır. E-08 metrikleri buradan gelir.
--    params_snapshot JSONB: koşu anındaki kural/parametre kopyası.
--    Burada JSONB DOĞRU seçim: içerik koşudan koşuya farklı yapıda olabilir, sadece arşiv
--    amaçlı okunur, tek tek düzenlenmez. (constraint_params'ta tersini seçmiştik, çünkü
--    orada her değer tek tek düzenleniyordu.)
CREATE TABLE solver_runs (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    draft_id           BIGINT        NOT NULL,
    status             TEXT          NOT NULL DEFAULT 'CALISIYOR',
    started_at         TIMESTAMPTZ   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at        TIMESTAMPTZ,
    time_limit_seconds INTEGER,
    objective_value    NUMERIC(14,2),
    params_snapshot    JSONB,
    CONSTRAINT fk_runs_draft FOREIGN KEY (draft_id) REFERENCES schedule_drafts(id) ON DELETE CASCADE,
    CONSTRAINT ck_runs_status CHECK (status IN ('CALISIYOR', 'OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'HATA')),
    CONSTRAINT ck_runs_finished_after_start CHECK (finished_at IS NULL OR finished_at >= started_at)
);

-- 3) Atama: "Ayşe, 14 Ekim, GECE" (taslağa bağlı)
--    work_date = vardiyanın BAŞLADIĞI gün. Gece 18:00'de başlıyorsa o günün tarihi yazılır.
--    UNIQUE (draft_id, staff_id, work_date): aynı taslakta bir kişi aynı güne iki vardiya ALAMAZ.
--    Bunu uygulama koduna değil veritabanına bıraktık (Yol Haritası Adım 6 isteği).
--    source: satırı kim üretti. onceki_ay = önceki ayın son günleri, değiştirilemez bağlam.
CREATE TABLE assignments (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    draft_id      BIGINT      NOT NULL,
    staff_id      BIGINT      NOT NULL,
    shift_type_id BIGINT      NOT NULL,
    work_date     DATE        NOT NULL,
    source        TEXT        NOT NULL DEFAULT 'solver',
    is_locked     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_assignments_draft FOREIGN KEY (draft_id)      REFERENCES schedule_drafts(id) ON DELETE CASCADE,
    CONSTRAINT fk_assignments_staff FOREIGN KEY (staff_id)      REFERENCES staff(id)           ON DELETE RESTRICT,
    CONSTRAINT fk_assignments_shift FOREIGN KEY (shift_type_id) REFERENCES shift_types(id)     ON DELETE RESTRICT,
    CONSTRAINT uq_assignments_draft_staff_date UNIQUE (draft_id, staff_id, work_date),
    CONSTRAINT ck_assignments_source CHECK (source IN ('solver', 'manuel', 'onceki_ay'))
);
-- ON DELETE seçimleri:
--   Taslak silinirse atamaları da gitsin          → CASCADE
--   Personel silinmeye çalışılırsa                  → RESTRICT (geçmiş kayıt korunur;
--                                                     ayrılan kişi staff.is_active = FALSE yapılır, bkz. 008)
--   Vardiya tipi silinmeye çalışılırsa             → RESTRICT

-- 4) Vardiya içi görevler: "Ayşe'nin 14 Ekim gecesi görevleri: TRIYAJ + AMBULANS"
--    Görev = yetkinlik kodu (3.2 kararı). Bir atamanın birden fazla görevi olabilir → köprü.
CREATE TABLE assignment_tasks (
    assignment_id BIGINT NOT NULL,
    competency_id BIGINT NOT NULL,
    PRIMARY KEY (assignment_id, competency_id),
    CONSTRAINT fk_tasks_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id)  ON DELETE CASCADE,
    CONSTRAINT fk_tasks_competency FOREIGN KEY (competency_id) REFERENCES competencies(id) ON DELETE RESTRICT
);

-- 5) Çözüm teşhisi (E-10): "14–20 Ekim çözülemedi, triyaj havuzu ile haftalık dinlenme çatışıyor"
--    constraint_id / staff_id / work_date boş olabilir: her teşhis bir kişiye ya da güne bağlı değildir.
CREATE TABLE solver_diagnostics (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    solver_run_id BIGINT      NOT NULL,
    severity      TEXT        NOT NULL,
    constraint_id BIGINT,
    staff_id      BIGINT,
    work_date     DATE,
    message       TEXT        NOT NULL,
    suggestion    TEXT,
    created_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_diag_run        FOREIGN KEY (solver_run_id) REFERENCES solver_runs(id)  ON DELETE CASCADE,
    CONSTRAINT fk_diag_constraint FOREIGN KEY (constraint_id) REFERENCES constraints(id)  ON DELETE SET NULL,
    CONSTRAINT fk_diag_staff      FOREIGN KEY (staff_id)      REFERENCES staff(id)        ON DELETE SET NULL,
    CONSTRAINT ck_diag_severity CHECK (severity IN ('cakisma', 'ihlal', 'uyari'))
);

-- 6) Gerçekleşen giriş-çıkış (arkadaşının isteği, faz 2 ama yapısı şimdiden hazır)
--    Plan değişmez; sapma olursa (hastalıkla erken çıkış, geç çıkış) buraya yazılır.
--    PRIMARY KEY = assignment_id → bir atamanın en fazla bir gerçekleşen kaydı olur (1–0..1 ilişki).
--    TIMESTAMPTZ (tarih + saat): gece vardiyasında çıkış ertesi gün olduğu için sadece saat yetmez.
--    actual_hours: çıkış − giriş, veritabanı hesaplar (crosses_midnight ile aynı teknik).
CREATE TABLE actual_times (
    assignment_id BIGINT       PRIMARY KEY,
    actual_start  TIMESTAMPTZ  NOT NULL,
    actual_end    TIMESTAMPTZ  NOT NULL,
    actual_hours  NUMERIC(5,2) GENERATED ALWAYS AS
        (ROUND((EXTRACT(EPOCH FROM (actual_end - actual_start)) / 3600)::numeric, 2)) STORED,
    reason        TEXT,
    updated_by    VARCHAR(100),
    updated_at    TIMESTAMPTZ  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_actual_assignment FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
    CONSTRAINT ck_actual_end_after_start CHECK (actual_end > actual_start)
);
