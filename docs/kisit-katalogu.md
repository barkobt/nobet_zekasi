# Kısıt Kataloğu

> Kaynak: Notion "Kısıt Kataloğu" veritabanı (22 satır, 25 Eylül 2026 itibarıyla).
> **Önemli:** Veritabanı çalışması sırasında bazı kararlar Notion'dan sonra güncellendi.
> `db/seeds` içindeki `constraints` / `constraint_params` verisi ile çelişki varsa
> **veritabanı doğrudur**; çelişkiyi raporla. Bilinen güncellemeler en altta.

Tip: **Hard** = asla ihlal edilemez · **Soft** = ihlal cezalandırılır (ağırlık) · **Tanım** = modelin girdisi, kısıt değil · **Kapsam Dışı** = saklı, varsayılan kapalı
Kaynak: **Yasal** = UI'da gevşetilemez · **Kurumsal** = gevşetilebilir · **Tercih** · **Belirsiz**

| Kod | Tip | Kapsam | Kaynak | Ağırlık | Kural |
|---|---|---|---|---|---|
| C-001 | Tanım | Vardiya | Kurumsal | — | Gündüz 08:30–18:00 (9,5 sa), Gece 18:00–08:30 (14,5 sa); aralarında boşluk yok. Devir teslim çalışma saatine dahil. |
| C-002 | Hard | Kişi | Belirsiz | — | 3 gece üst üste çalışılamaz (2 gece serbest). |
| C-003 | Soft | Hafta | Kurumsal | 10 | Haftalık 50 saat referans değer; sapma cezalandırılır, yasaklanmaz. |
| C-004 | Hard | Ay | Kurumsal | — | Kişi başı aylık en az 200 saat. İzinli/raporlu günlerde hedef orantılı küçülür (gün başına düşüm miktarı açık soru). |
| C-005 | Hard | Vardiya | Kurumsal | — | Gündüz EN AZ 6 kişi (fazlası sorun değil), 1'i sorumlu. |
| C-006 | Hard | Vardiya | Kurumsal | — | Gece EN AZ 5 kişi, sorumlu yok. |
| C-007 | Hard | Vardiya | Kurumsal | — | Her vardiyada en az 1 shift yetkilisi (ekip lideri). Ekip lideri triyaj/ambulans da alabilir. |
| C-008 | Hard | Hafta | Kurumsal | — | Sorumlu (tek kişi): hafta içi 08:30–18:00, Cumartesi 08:30–14:00, Pazar izinli. |
| C-009 | Hard | Vardiya | Kurumsal | — | Ambulans görevi için 2 kişi (bkz. güncelleme notu). |
| C-010 | Hard | Vardiya | Kurumsal | — | Gözlem alanında 2 yetkin kişi; triyaj görevindekilerden FARKLI. |
| C-011 | Hard | Vardiya | Kurumsal | — | Triyajda EN AZ 3 yetkin kişi; gözlem görevindekilerden FARKLI. |
| C-012 | Tanım | Kişi | Kurumsal | — | Yetkinlik tanımları (eğitim hemşiresi kaydını tutar). |
| C-013 | Soft | Vardiya | Kurumsal | 40 | Uyumsuz kişiler aynı vardiyaya yazılırsa ceza. |
| C-014 | Hard | Kişi | Kurumsal | — | 2 gece art arda çalışıldıysa 24 saat yasal boşluk zorunlu; 08:30'dan itibaren sayılır. |
| C-015 | Tanım | Kişi | Kurumsal | — | [C-014 ile birleşti] Gündüz→gündüz geçişi serbest; genel "her vardiya arası 24h" kuralı yok. |
| C-016 | Hard | Hafta | Yasal | — | Haftada EN AZ 1 dinlenme olayı: izin günü VEYA 2 gece sonrası 24h boşluk (biri yeterli). |
| C-017 | Hard | Kişi | Kurumsal | — | Sadece gündüz çalışabilen personel geceye yazılamaz. |
| C-018 | Kapsam Dışı | Vardiya | Tercih | — | 24 saatlik vardiya kullanılmaz (`enable_24h` bayrağı, varsayılan kapalı). |
| C-019 | Hard | Vardiya | Kurumsal | — | Ambulans/gözlem görevleri vardiya mevcudunun İÇİNDEN atanır (ayrı kadro değil). |
| C-020 | Hard | Kişi | Kurumsal | — | Oryantasyondaki yeni personel eğitim hemşiresiyle birebir çalışır. |
| O-001 | Soft (amaç) | Ay | Kurumsal | 200 | Aylık 200 saat üzeri fazla mesai toplamını minimize et. |
| O-002 | Soft (amaç) | Ay | Kurumsal | 220 | Kişiler arası saat dağılımını dengele (max–min farkı). **Adalet en önemli başarı kriteri.** |

## Veritabanı çalışmasında sonradan değişenler (şema bunlara göre kuruldu)
- **Ambulans kuralı** artık triyaj havuzuna bağlı değil; bağımsız görev/yetkinlik olarak modellendi.
- **Sayım yetkisi** ile **ekip lideri** ayrı yetkinlikler.
- Süpervizörler ve oryantasyondaki personel günlük mevcut (C-005/C-006) sayımına dahil edilmez.
- Kısa gece vardiya tipi (GECE_0100) kaldırıldı.
- Merve Armut yalnızca gündüz çalışır (C-017 kapsamında).

## Bilinen açık sorular
- C-004: izin/rapor günü başına hedeften kaç saat düşülecek.
- C-016: hafta sınırını aşan 24h boşluk hangi haftaya sayılır.
- C-008: sorumlu izinliyken yerine kim bakar.
