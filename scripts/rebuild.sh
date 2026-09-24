#!/bin/bash
# scripts/rebuild.sh
# nobet_zekasi veritabanını sıfırdan kurar: şemayı temizler, tüm migration'ları ve seed'leri sırayla çalıştırır.
# Kullanım (repo klasöründe):   ./scripts/rebuild.sh
# Farklı kullanıcı/port için:    PGUSER=postgres PGPORT=5432 ./scripts/rebuild.sh
set -e                                   # bir dosya hata verirse dur, devam etme
DB="${PGDATABASE:-nobet_zekasi}"
PSQL="psql -d $DB -v ON_ERROR_STOP=1 -q"  # ON_ERROR_STOP: SQL hatasında psql'i durdur

echo "Hedef veritabanı: $DB"
read -p "public şemasındaki HER ŞEY silinecek. Devam? (e/h) " ok
[ "$ok" = "e" ] || { echo "İptal."; exit 1; }

$PSQL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
for f in migrations/*.up.sql; do echo "↑ $f"; $PSQL -f "$f"; done
for f in seeds/*.sql;         do echo "• $f"; $PSQL -f "$f" > /dev/null; done

$PSQL -c "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') AS tablo,
                 (SELECT count(*) FROM information_schema.views  WHERE table_schema='public') AS view,
                 (SELECT count(*) FROM staff) AS personel,
                 (SELECT count(*) FROM assignments) AS atama;"
echo "Bitti. Beklenen: 22 tablo, 5 view, 20 personel, 91 atama."
