#!/bin/bash
# db/scripts/rebuild.sh
# Veritabanını sıfırdan kurar: public şemasını temizler, tüm migration ve seed'leri sırayla çalıştırır.
#
# Kullanım (nereden çağrıldığı önemli değil):
#   ./db/scripts/rebuild.sh                     → yerel veritabanı (PGDATABASE, varsayılan nobet_zekasi)
#   DATABASE_URL="postgres://..." ./db/scripts/rebuild.sh   → Neon / uzak veritabanı
#   ./db/scripts/rebuild.sh --yes               → onay sorma (CI, ilk kurulum)
set -euo pipefail

# Betik nerede olursa olsun db/ kökünden çalış: migrations/ ve seeds/ göreli yolları sabit kalsın.
DB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DB_ROOT"

ASSUME_YES=0
[ "${1:-}" = "--yes" ] && ASSUME_YES=1

# Bağlantı: DATABASE_URL varsa onu kullan (Neon pooled + sslmode=require dahil),
# yoksa yerel psql varsayılanlarına düş.
if [ -n "${DATABASE_URL:-}" ]; then
    PSQL=(psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -q)
    # Parolayı ekrana basma: yalnız host ve veritabanı adını göster.
    HEDEF="$(printf '%s' "$DATABASE_URL" | sed -E 's#^[^:]+://([^@]*@)?#\1#; s#^[^@]*@##; s#\?.*##')"
else
    PSQL=(psql -d "${PGDATABASE:-nobet_zekasi}" -v ON_ERROR_STOP=1 -q)
    HEDEF="${PGDATABASE:-nobet_zekasi} (yerel)"
fi

echo "Hedef veritabanı: $HEDEF"
if [ "$ASSUME_YES" -eq 0 ]; then
    read -r -p "public şemasındaki HER ŞEY silinecek. Devam? (e/h) " ok
    [ "$ok" = "e" ] || { echo "İptal."; exit 1; }
fi

"${PSQL[@]}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
for f in migrations/*.up.sql; do echo "↑ $f"; "${PSQL[@]}" -f "$f"; done
# Seed 009 referans haftayı kağıttan aktarır ve bilinen tek uygunluk ihlalini içerir
# (Güven Göl, 26.09, AMBULANS). Trigger bunu WARNING olarak geçirir — beklenen davranış.
for f in seeds/*.sql;         do echo "• $f"; "${PSQL[@]}" -f "$f" > /dev/null; done

"${PSQL[@]}" -c "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') AS tablo,
                        (SELECT count(*) FROM information_schema.views  WHERE table_schema='public') AS view,
                        (SELECT count(*) FROM staff) AS personel,
                        (SELECT count(*) FROM assignments) AS atama,
                        (SELECT count(*) FROM v_task_eligibility_violations) AS uygunluk_ihlali;"
echo "Bitti. Beklenen: 22 tablo, 6 view, 20 personel, 91 atama, 1 uygunluk ihlali."
