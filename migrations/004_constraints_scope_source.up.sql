--Kuralın nerede geçerli olduğu (kapsam) ve gevşetilebilir mi(kaynak)

ALTER TABLE constraints
	ADD column scope TEXT NOT NULL,
	ADD column source TEXT NOT NULL;

ALTER TABLE constraints
	ADD CONSTRAINT ck_constraints_scope
	CHECK (scope IN ('kisi','vardiya', 'gun', 'hafta', 'ay'));


ALTER TABLE constraints
	ADD CONSTRAINT ck_constraints_source
	CHECK (source IN ('yasal','kurumsal', 'tercih', 'belirsiz'));