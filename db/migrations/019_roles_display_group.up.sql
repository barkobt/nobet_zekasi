-- 019_roles_display_group.up.sql
-- Rol → ızgara grubu ve sıra. Bugün bu bilgi web tarafında sabit bir dizide duruyor;
-- yeni bir rol eklendiğinde ızgarada hiçbir gruba düşmüyor ve sessizce kayboluyordu.

ALTER TABLE roles
    ADD COLUMN display_group VARCHAR(40),
    ADD COLUMN sort_order    INTEGER;

COMMENT ON COLUMN roles.display_group IS
    'Çizelge ızgarasında ve personel listesinde satırların toplandığı grup adı.';
COMMENT ON COLUMN roles.sort_order IS
    'Grup içindeki sıra. Küçük olan üstte.';
