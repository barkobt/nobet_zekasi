#!/bin/bash
# db/scripts/rebuild.sh
# Veritabanını sıfırdan kurar: public şemasını temizler, tüm migration ve seed'leri sırayla çalıştırır.
#
# Kullanım (nereden çağrıldığı önemli değil):
#   ./db/scripts/rebuild.sh                     → yerel veritabanı (PGDATABASE, varsayılan nobet_zekasi)
#   DATABASE_URL_DIRECT="postgres://..." ./db/scripts/rebuild.sh   → Neon / uzak veritabanı
#   ./db/scripts/rebuild.sh --yes               → onay sorma (CI, ilk kurulum)
#
# NEON'DA POOLED DEĞİL, DIRECT BAĞLANTI KULLAN.
# Pooled uç (…-pooler.…) PgBouncer'ın transaction modunda çalışır: bağlantı her
# ifadeden sonra başka bir istemciye geçebilir. Şema kurulumu buna dayanmaz —
# CREATE EXTENSION, geçici tablolar (seeds/007 ve 009 kullanıyor) ve uzun
# transaction'lar oturumun aynı kalmasını ister. Bu yüzden:
#   DATABASE_URL_DIRECT → şema/migration (yalnız kurulum anında, yerelden)
#   DATABASE_URL        → uygulama (pooled, Railway'de)
# Betik ikisini de kabul eder ama DIRECT olanı tercih eder.
set -euo pipefail

# Betik nerede olursa olsun db/ kökünden çalış: migrations/ ve seeds/ göreli yolları sabit kalsın.
DB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DB_ROOT"

ASSUME_YES=0
[ "${1:-}" = "--yes" ] && ASSUME_YES=1

# Bağlantı: DATABASE_URL varsa onu kullan (Neon pooled + sslmode=require dahil),
# yoksa yerel psql varsayılanlarına düş.
# Değişken TANIMLI ama BOŞ ise sessizce yerele düşme: kullanıcı uzak bir veritabanı
# hedefliyordu ve yapıştırma tutmamış demektir. Yerele yazmak sessiz bir veri kaybıdır.
for degisken in DATABASE_URL_DIRECT DATABASE_URL; do
    if [ -n "${!degisken+tanimli}" ] && [ -z "${!degisken}" ]; then
        echo "HATA: $degisken tanımlı ama boş." >&2
        echo "      Uzak bir veritabanı hedeflediysen bağlantı dizesi okunamamış olabilir" >&2
        echo "      (örn. 'read -s' ile yapıştırma tutmadı). Yerel veritabanına yazmıyorum." >&2
        echo "      Kontrol:  echo \"uzunluk: \${#$degisken}\"" >&2
        echo "      Yerel kurulum istiyorsan değişkeni tamamen kaldır:  unset $degisken" >&2
        exit 1
    fi
done

KURULUM_URL="${DATABASE_URL_DIRECT:-${DATABASE_URL:-}}"

if [ -n "$KURULUM_URL" ]; then
    PSQL=(psql "$KURULUM_URL" -v ON_ERROR_STOP=1 -q)
    # Parolayı ekrana basma: yalnız host ve veritabanı adını göster.
    HEDEF="UZAK → $(printf '%s' "$KURULUM_URL" | sed -E 's#^[^:]+://([^@]*@)?#\1#; s#^[^@]*@##; s#\?.*##')"

    # Pooled uçla şema kurmaya çalışırsa uyar: hata mesajları kafa karıştırıcı olur.
    case "$KURULUM_URL" in
      *-pooler.*)
        echo "UYARI: pooled (PgBouncer) bir uç kullanıyorsun." >&2
        echo "       Şema kurulumu DIRECT bağlantı ister; Neon konsolunda" >&2
        echo "       'Connection pooling' kapalıyken görünen adresi kullan." >&2
        echo "       Devam edersen CREATE EXTENSION veya geçici tablolarda hata alabilirsin." >&2
        ;;
    esac
else
    PSQL=(psql -d "${PGDATABASE:-nobet_zekasi}" -v ON_ERROR_STOP=1 -q)
    HEDEF="YEREL → ${PGDATABASE:-nobet_zekasi}"
fi

echo "Hedef veritabanı: $HEDEF"
if [ "$ASSUME_YES" -eq 0 ]; then
    read -r -p "public şemasındaki HER ŞEY silinecek. Devam? (e/h) " ok
    [ "$ok" = "e" ] || { echo "İptal."; exit 1; }
fi

# Yalnızca KANONİK adlar çalıştırılır: 001_ad.up.sql / 001_ad.sql
# Senkron araçları (iCloud, Dropbox) "001_ad.up 2.sql" gibi kopyalar bırakabiliyor;
# bunlar seeds/*.sql kalıbına takılıp iki kez çalışır ve zamanla bayatlayıp
# ESKİ SQL'i yeni şemanın üstüne uygular. Sessizce atlamak yerine uyarıyoruz.
gecerli_mi() { [[ "$(basename "$1")" =~ ^[0-9]{3}_[A-Za-z0-9_]+(\.(up|down))?\.sql$ ]]; }

atlanan=0
for f in migrations/*.sql seeds/*.sql; do
    gecerli_mi "$f" || { echo "⚠ atlandı (kanonik olmayan ad): $f" >&2; atlanan=$((atlanan+1)); }
done
[ "$atlanan" -gt 0 ] && echo "⚠ $atlanan dosya atlandı. Kopya dosyaları silmen önerilir." >&2

"${PSQL[@]}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
for f in migrations/*.up.sql; do gecerli_mi "$f" || continue; echo "↑ $f"; "${PSQL[@]}" -f "$f"; done
# Seed 009 referans haftayı kağıttan aktarır ve bilinen tek uygunluk ihlalini içerir
# (Güven Göl, 26.09, AMBULANS). Trigger bunu WARNING olarak geçirir — beklenen davranış.
for f in seeds/*.sql; do gecerli_mi "$f" || continue; echo "• $f"; "${PSQL[@]}" -f "$f" > /dev/null; done

"${PSQL[@]}" -c "SELECT (SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE') AS tablo,
                        (SELECT count(*) FROM information_schema.views  WHERE table_schema='public') AS view,
                        (SELECT count(*) FROM staff) AS personel,
                        (SELECT count(*) FROM assignments) AS atama,
                        (SELECT count(*) FROM v_task_eligibility_violations) AS uygunluk_ihlali;"
echo "Bitti. Beklenen: 22 tablo, 6 view, 20 personel, 91 atama, 1 uygunluk ihlali."
