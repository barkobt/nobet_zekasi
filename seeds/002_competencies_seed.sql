--seeds/002_competencies_seed.sql

INSERT INTO competencies (code,name,description) VALUES
	('IV', 'IV kateterizasyon/damar yolu', 'Damar yolu açabilme yetkinliği'),
	('IM', 'İM enjeksiyon', NULL),
	('HASTA_ILT', 'Hasta iletişimi', 'Triyaj ve karşılamada gerekli yetkinlik'),
	('SHIFT_YETKILISI', 'Shift yetkilisi','Vardiya devri ve ekip liderliği/sayım yetkilisi'),
	('TRIYAJ','Triyaj' ,'Gözlem havuzundan ayrık çalışır'),
	('AMBULANS', 'Ambulans görevi', 'NULL'),
	('GOZLEM','Gözlem alanı' ,'Triyaj havuzundan ayrık çalışır') 
ON CONFLICT (code) DO NOTHING;

SELECT id, code, name FROM competencies ORDER BY id;

