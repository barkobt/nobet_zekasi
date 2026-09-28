-- 017_visible_counters.up.sql
-- Izgarada hangi sayaçların görüneceği. Ayar veritabanında: "bu ay gece sayısını da
-- görelim" dendiğinde deploy gerekmez (E-03'teki kural ayarlarıyla aynı mantık).
--
-- Sayacın NE hesapladığı koddadır (repositories/schedule.py), AÇIK/KAPALI olması
-- burada. İkisi 'key' ile eşleşir.

CREATE TABLE visible_counters (
    key          VARCHAR(16)  PRIMARY KEY,           -- ASCII: API ve JSON anahtarı
    badge        VARCHAR(8)   NOT NULL,              -- ızgarada görünen kısaltma (GÖZ, İST)
    label        VARCHAR(80)  NOT NULL,
    description  TEXT,
    sort_order   INTEGER      NOT NULL,
    always_shown BOOLEAN      NOT NULL DEFAULT FALSE, -- "Detayları göster"dan bağımsız (G, N, S)
    weekly_on    BOOLEAN      NOT NULL DEFAULT FALSE,
    monthly_on   BOOLEAN      NOT NULL DEFAULT FALSE,
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_visible_counters_sort UNIQUE (sort_order),
    -- Her zaman görünen bir sayaç kapatılamaz: satır özeti G · N · S olmadan okunmaz.
    CONSTRAINT ck_visible_counters_always
        CHECK (NOT always_shown OR (weekly_on AND monthly_on))
);

COMMENT ON TABLE visible_counters IS
    'Izgara satır özetinde ve alt barda görünen sayaçlar. Haftalık ve aylık görünüm için ayrı açma/kapama.';
