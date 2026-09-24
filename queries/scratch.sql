SELECT * FROM constraints;

SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;


SELECT id, 'Ecem Urcan', 'gunduz_gece' FROM roles WHERE code = 'hemsire';