#!/bin/bash
# db/scripts/migrate.sh
# Yalnız UYGULANMAMIŞ migration'ları sırayla uygular. Veriyi silmez.
#
# rebuild.sh'ten farkı: o şemayı sıfırlar (yerel geliştirme için), bu ise
# mevcut veriyi koruyarak ilerler. Canlıda (Neon) HER ZAMAN bu kullanılır.
#
# Kullanım:
#   DATABASE_URL_DIRECT="postgres://..." ./db/scripts/migrate.sh
#   ./db/scripts/migrate.sh --seed          → seed'leri de çalıştır (ilk kurulum)
#   ./db/scripts/migrate.sh --mark-applied  → çalıştırmadan "uygulandı" diye işaretle
#   ./db/scripts/migrate.sh --status        → ne uygulanmış, ne bekliyor
set -euo pipefail

DB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DB_ROOT"

MOD="uygula"
for arg in "$@"; do
  case "$arg" in
    --seed)          MOD="seed" ;;
    --mark-applied)  MOD="isaretle" ;;
    --status)        MOD="durum" ;;
    *) echo "Bilinmeyen seçenek: $arg" >&2; exit 1 ;;
  esac
done

for degisken in DATABASE_URL_DIRECT DATABASE_URL; do
    if [ -n "${!degisken+tanimli}" ] && [ -z "${!degisken}" ]; then
        echo "HATA: $degisken tanımlı ama boş. Yanlış veritabanına yazmamak için duruyorum." >&2
        exit 1
    fi
done

URL="${DATABASE_URL_DIRECT:-${DATABASE_URL:-}}"
if [ -n "$URL" ]; then
    PSQL=(psql "$URL" -v ON_ERROR_STOP=1 -q -t -A)
    HEDEF="UZAK → $(printf '%s' "$URL" | sed -E 's#^[^:]+://([^@]*@)?#\1#; s#^[^@]*@##; s#\?.*##')"
    case "$URL" in
      *-pooler.*) echo "UYARI: pooled uç. Migration DIRECT bağlantı ister." >&2 ;;
    esac
else
    PSQL=(psql -d "${PGDATABASE:-nobet_zekasi}" -v ON_ERROR_STOP=1 -q -t -A)
    HEDEF="YEREL → ${PGDATABASE:-nobet_zekasi}"
fi
echo "Hedef: $HEDEF"

# Kayıt tablosu. Bu bir migration DEĞİL: migration'ları izleyen aracın kendi
# defteri, dolayısıyla migration olarak yazılamaz (tavuk-yumurta).
"${PSQL[@]}" -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);" > /dev/null

uygulanmis() { "${PSQL[@]}" -c "SELECT 1 FROM schema_migrations WHERE version = '$1'" | grep -q 1; }
kaydet()     { "${PSQL[@]}" -c "INSERT INTO schema_migrations (version) VALUES ('$1')
                                ON CONFLICT DO NOTHING" > /dev/null; }

gecerli_mi() { [[ "$(basename "$1")" =~ ^[0-9]{3}_[A-Za-z0-9_]+(\.(up|down))?\.sql$ ]]; }

# ---------------------------------------------------------------- durum
if [ "$MOD" = "durum" ]; then
    echo "--- migration ---"
    for f in migrations/*.up.sql; do
        gecerli_mi "$f" || continue
        v="$(basename "$f" .up.sql)"
        uygulanmis "$v" && echo "  ✓ $v" || echo "  · $v (bekliyor)"
    done
    echo "--- seed ---"
    for f in seeds/*.sql; do
        gecerli_mi "$f" || continue
        v="seed:$(basename "$f" .sql)"
        uygulanmis "$v" && echo "  ✓ $(basename "$f")" || echo "  · $(basename "$f") (çalışmadı)"
    done
    exit 0
fi

# ------------------------------------------------------------ işaretle
# Mevcut bir veritabanını "bu migration'lar zaten uygulanmış" diye kaydeder.
# Hiçbir SQL ÇALIŞTIRMAZ — yalnız deftere yazar.
if [ "$MOD" = "isaretle" ]; then
    sayi=0
    for f in migrations/*.up.sql; do
        gecerli_mi "$f" || continue
        v="$(basename "$f" .up.sql)"
        uygulanmis "$v" || { kaydet "$v"; echo "  işaretlendi: $v"; sayi=$((sayi+1)); }
    done
    for f in seeds/*.sql; do
        gecerli_mi "$f" || continue
        kaydet "seed:$(basename "$f" .sql)"
    done
    echo "Bitti. $sayi migration uygulanmış olarak işaretlendi (hiçbiri çalıştırılmadı)."
    exit 0
fi

# -------------------------------------------------------------- uygula
bekleyen=0
for f in migrations/*.up.sql; do
    gecerli_mi "$f" || { echo "⚠ atlandı (kanonik olmayan ad): $f" >&2; continue; }
    v="$(basename "$f" .up.sql)"
    uygulanmis "$v" && continue

    echo "↑ $v"
    # Her migration KENDİ transaction'ında: yarıda kalırsa şema bozulmaz.
    # psql tek dosyayı BEGIN/COMMIT arasına alır; hata olursa ON_ERROR_STOP ile çıkar.
    if ! "${PSQL[@]}" --single-transaction -f "$f"; then
        echo "HATA: $v uygulanamadı. Değişiklikler geri alındı." >&2
        exit 1
    fi
    kaydet "$v"
    bekleyen=$((bekleyen+1))
done
[ "$bekleyen" -eq 0 ] && echo "Uygulanacak yeni migration yok."

# --------------------------------------------------------------- seed
# Seed'ler canlıda YALNIZ ilk kurulumda koşar: her biri deftere yazılır,
# ikinci çağrıda atlanır. Elle girilen veri böylece üzerine yazılmaz.
if [ "$MOD" = "seed" ]; then
    for f in seeds/*.sql; do
        gecerli_mi "$f" || continue
        v="seed:$(basename "$f" .sql)"
        uygulanmis "$v" && { echo "• $(basename "$f") — zaten çalışmış, atlandı"; continue; }
        echo "• $(basename "$f")"
        # Seed'ler kendi BEGIN/COMMIT'lerini taşıyor (007, 008, 009, 011, 012);
        # --single-transaction eklersek iç içe transaction uyarısı verirler.
        "${PSQL[@]}" -f "$f" > /dev/null
        kaydet "$v"
    done
fi

"${PSQL[@]}" -c "SELECT 'tablo=' || (SELECT count(*) FROM information_schema.tables
                   WHERE table_schema='public' AND table_type='BASE TABLE')
              || ' view='  || (SELECT count(*) FROM information_schema.views WHERE table_schema='public')
              || ' migration=' || (SELECT count(*) FROM schema_migrations WHERE version NOT LIKE 'seed:%')"
